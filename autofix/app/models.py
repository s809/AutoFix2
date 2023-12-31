import sys
from django.db import connection, models
from django.db.models import Sum, Q
from django.contrib.auth.models import *
from django.core.validators import MaxValueValidator, MinValueValidator, MinLengthValidator
from django.forms import ValidationError
from softdelete.models import SoftDeleteObject
from phonenumber_field.modelfields import PhoneNumberField
from django.utils import timezone
from django.urls import reverse

datetime_format = "%d.%m.%Y"

def validate_item_count(current, item, name, is_negative = False):
    # Calculate the total quantity of the item based on WarehouseRestock and WarehouseUse objects
    total_quantity = item.get_count(current)
    add = getattr(current, name)

    # Calculate the new total quantity if the current operation is successful
    new_total_quantity = total_quantity + add * (-1 if is_negative else 1)

    # Check if the new total quantity is less than 0
    if new_total_quantity < 0:
        raise ValidationError(
            {name: f"Недостаточно единиц расходника. Требуется еще {-new_total_quantity} шт., имеется: {total_quantity} шт."}
        )

class FullTextSearchMixin:
    search_initialized = False

    @staticmethod
    def initialize_search(cls):
        if cls.search_initialized:
            return

        model_name = cls.__name__.lower()
        field_defs = cls.get_search_field_defs()

        def make_insert_stmt():
            return f"""
                INSERT INTO app_{model_name}_search
                    SELECT {", ".join(
                        [f"app_{model_name}.{field}" for field in field_defs[0][1]] +
                        [", ".join([f"{fk_name}.{field} AS {fk_name}_{field}" for field in fields]) for [jcls, fields, fk_name] in field_defs[1:]]
                    )}
                    FROM app_{model_name}
                    {" ".join([f"JOIN app_{jcls.__name__.lower()} {fk_name} ON {jcls.__name__.lower()}.id = app_{model_name}.{fk_name}_id" for [jcls, fields, fk_name] in field_defs[1:]])}
                    WHERE 1
                        {f"AND app_{model_name}.deleted_at IS NULL" if hasattr(cls, "deleted_at") else ""}
            """
        def make_delete_stmt():
            return f"DELETE FROM app_{model_name}_search WHERE id = old.id;"

        with connection.cursor() as cursor:
            cursor.execute(f"DROP TABLE IF EXISTS app_{model_name}_search;")
            if not ('makemigrations' in sys.argv or 'migrate' in sys.argv):
                cursor.execute(f"""
                    CREATE VIRTUAL TABLE app_{model_name}_search USING FTS5({",".join(field_defs[0][1] + [",".join([f"{fk_name}_{field}" for field in fields]) for [jcls, fields, fk_name] in field_defs[1:]])});
                """)
                cursor.execute(make_insert_stmt() + ";")

            cursor.execute(f"DROP TRIGGER IF EXISTS app_{model_name}_search_insert;")
            if not ('makemigrations' in sys.argv or 'migrate' in sys.argv):
                cursor.execute(f"""
                    CREATE TRIGGER app_{model_name}_search_insert AFTER INSERT ON app_{model_name} BEGIN
                        {make_insert_stmt()} AND app_{model_name}.id = new.id;
                    END;
                """)

            cursor.execute(f"DROP TRIGGER IF EXISTS app_{model_name}_search_update;")
            if not ('makemigrations' in sys.argv or 'migrate' in sys.argv):
                cursor.execute(f"""
                    CREATE TRIGGER app_{model_name}_search_update AFTER UPDATE ON app_{model_name} BEGIN
                        {make_delete_stmt()}
                        {make_insert_stmt()} AND app_{model_name}.id = new.id;
                    END;
                """)

            for [jcls, fields, fk_name] in field_defs[1:]:
                cursor.execute(f"DROP TRIGGER IF EXISTS app_{model_name}_search_update_by_{fk_name};")
                if not ('makemigrations' in sys.argv or 'migrate' in sys.argv):
                    cursor.execute(f"""
                        CREATE TRIGGER app_{model_name}_search_update_by_{fk_name} AFTER UPDATE ON app_{jcls.__name__.lower()} BEGIN
                            DELETE FROM app_{model_name}_search
                                WHERE id IN (SELECT id FROM app_{model_name} WHERE {fk_name}_id = old.id);
                            {make_insert_stmt()} AND app_{model_name}.{fk_name}_id = new.id;
                        END;
                    """)

            cursor.execute(f"DROP TRIGGER IF EXISTS app_{model_name}_search_delete;")
            if not ('makemigrations' in sys.argv or 'migrate' in sys.argv):
                cursor.execute(f"""
                    CREATE TRIGGER app_{model_name}_search_delete AFTER DELETE ON app_{model_name} BEGIN
                        {make_delete_stmt()}
                    END;
                """)

        cls.search_initialized = True

    @classmethod
    def get_search_field_defs_with_key(cls, fk_name: str | None):
        return (
            cls,
            (["id"] if not fk_name else []) +
                [key for [key, value] in cls.__dict__.items()
                 if hasattr(value, "field") and isinstance(value.field, (models.CharField, PhoneNumberField))],
            fk_name
        )

    @classmethod
    def get_search_field_defs(cls):
        return [cls.get_search_field_defs_with_key(None)]

    @classmethod
    def search(cls, search: str):
        with connection.cursor() as cursor:
            cursor.execute(f"""
                SELECT id FROM app_{cls.__name__.lower()}_search (%s);
            """, [" ".join([f"\"{s}\"" for s in search.split()])])
            results = cursor.fetchall()
        return Q(id__in=[result[0] for result in results])


class Employee(FullTextSearchMixin, AbstractUser):
    morphed_name = "сотрудника"
    def get_absolute_url(self):
        return reverse("employee", kwargs={"pk": self.pk})

    class Position(models.TextChoices):
        Administrator = 'AD', "Администратор"
        WarehouseManager = 'WM', "Менеджер запчастей"
        ServiceManager = "SM", "Менеджер сервиса"
        Mechanic = "ME", "Механик"
        Cashier = "CA", "Кассир"

    first_name = models.CharField("Имя", max_length=50)
    last_name = models.CharField("Фамилия", max_length=50)
    patronymic = models.CharField("Отчество", max_length=50)
    passport_info = models.CharField("Паспортные данные", max_length=150)
    position = models.CharField("Должность", max_length=2, choices=Position.choices)
    end_date = models.DateField("Дата увольнения", blank=True, null=True)
    end_reason = models.CharField("Причина увольнения", max_length=150, blank=True)

    create_allowed_to = []
    edit_allowed_to = []

    card_icon = "user"
    def card_title(self):
        return self.full_name()
    def card_tags(self):
        if not self.end_date:
            return None
        return { self.end_date_reason(): "warning" if self.end_reason else "secondary" }
    def card_subtitle(self):
        return self.get_position_display()

    def full_name(self):
        return f"{self.last_name} {self.first_name} {self.patronymic}"
    def end_date_reason(self, parens = False):
        if not self.end_date:
            return ""
        result = "Уволен " + self.end_date.strftime(datetime_format)
        if self.end_reason:
            result += ". Причина: " + self.end_reason
        return f" ({result})" if parens else result

    def clean(self):
        if self.end_reason and not self.end_date:
            raise ValidationError({
                "end_reason": "Причина увольнения не может быть указана без даты."
            })
        if self.end_date and self.end_date < self.date_joined.date():
            raise ValidationError({
                "end_date": "Дата увольнения не может раньше даты наема.",
            })
        self.is_active = not self.end_date

    def __str__(self) -> str:
        return self.full_name() + self.end_date_reason(True)
FullTextSearchMixin.initialize_search(Employee)


class Service(FullTextSearchMixin, SoftDeleteObject, models.Model):
    morphed_name = "услуги"
    def get_absolute_url(self):
        return reverse("service", kwargs={"pk": self.pk})

    name = models.CharField("Наименование", max_length=50)
    price = models.DecimalField("Цена", max_digits=7, decimal_places=2, validators=[MinValueValidator(0)])

    create_allowed_to = [Employee.Position.ServiceManager]
    edit_allowed_to = [Employee.Position.ServiceManager]

    card_icon = "gear"
    def card_title(self):
        return self.name
    def card_subtitle(self):
        return f"{self.price} руб."

    def __str__(self):
        return f"{self.name} ({self.price} руб.)"
FullTextSearchMixin.initialize_search(Service)


class Client(FullTextSearchMixin, SoftDeleteObject, models.Model):
    morphed_name = "клиента"

    def get_absolute_url(self):
        return reverse("client", kwargs={"pk": self.pk})

    full_name = models.CharField("ФИО", max_length=100)
    phone_number = PhoneNumberField("Номер телефона", region="RU")

    create_allowed_to = [Employee.Position.ServiceManager]
    edit_allowed_to = [Employee.Position.ServiceManager]

    card_icon = "address-card"
    def card_title(self):
        return self.full_name
    def card_subtitle(self):
        return self.phone_number

    def __str__(self) -> str:
        return f"{self.full_name} ({self.phone_number})"
FullTextSearchMixin.initialize_search(Client)


class Vehicle(FullTextSearchMixin, SoftDeleteObject, models.Model):
    morphed_name = "автомобиля"

    def get_absolute_url(self):
        return reverse("vehicle", kwargs={"pk": self.pk})

    manufacturer = models.CharField("Производитель", max_length=50)
    model = models.CharField("Модель", max_length=50)
    year = models.IntegerField("Год выпуска", validators=[MinValueValidator(1900), MaxValueValidator(2100)])
    license_number = models.CharField("Гос. номер", max_length=15)
    vin = models.CharField("VIN автомобиля", max_length=17, validators=[MinLengthValidator(17)])

    create_allowed_to = [Employee.Position.ServiceManager]
    edit_allowed_to = [Employee.Position.ServiceManager]

    card_icon = "car-side"
    def card_title(self):
        return f"{self.manufacturer} {self.model} {self.year} г."
    def card_subtitle(self):
        return f"Гос. номер: {self.license_number}"
    def card_subtitle_extra(self):
        return f"VIN: {self.vin}"

    def __str__(self) -> str:
        return f"{self.vin} {self.license_number} {self.manufacturer} {self.model} {self.year} г."
FullTextSearchMixin.initialize_search(Vehicle)


class RepairOrder(FullTextSearchMixin, SoftDeleteObject, models.Model):
    morphed_name = "заявки"
    def get_absolute_url(self):
        return reverse("order", kwargs={"pk": self.pk})

    master = models.ForeignKey(Employee, on_delete=models.DO_NOTHING, limit_choices_to={"position": Employee.Position.Mechanic, "end_date__isnull": True}, verbose_name="Мастер")

    client = models.ForeignKey(Client, on_delete=models.DO_NOTHING, verbose_name="Клиент")
    vehicle = models.ForeignKey(Vehicle, on_delete=models.DO_NOTHING, verbose_name="Автомобиль")
    vehicle_mileage = models.IntegerField("Пробег автомобиля, км", validators=[MinValueValidator(0)])

    start_date = models.DateField("Дата записи", default=timezone.now)
    finish_until = models.DateField("Завершить до", blank=True, null=True)
    finish_date = models.DateField("Дата завершения", blank=True, null=True)
    is_cancelled = models.BooleanField("Отменена")

    complaints = models.CharField("Описание проблемы", max_length=2000)
    diagnostic_results = models.CharField("Результаты диагностики", max_length=2000, blank=True)
    comments = models.CharField("Комментарии сервиса", max_length=300, blank=True)

    is_paid = models.BooleanField("Оплачено", default=False)
    is_warranty = models.BooleanField("Гарантийный ремонт", default=False)

    create_allowed_to = [Employee.Position.ServiceManager]
    edit_allowed_to = [Employee.Position.ServiceManager,
                       Employee.Position.Mechanic,
                       Employee.Position.Cashier]

    def clean(self):
        errors = {}
        if self.is_warranty:
            self.is_paid = bool(self.finish_date and not self.is_cancelled)
        if self.finish_until and self.finish_until < self.start_date:
            errors.update({
                "finish_until": "Дата запланированного завершения заявки не может раньше даты начала."
            })
        if self.is_cancelled and not self.finish_date:
            errors.update({
                "is_cancelled": "Для отмены заявки на ремонт требуется дата завершения."
            })
        if self.finish_date and self.finish_date < self.start_date:
            errors.update({
                "finish_date": "Дата завершения заявки на ремонт не может раньше даты начала.",
            })
        if len(errors):
            raise ValidationError(errors)

    @classmethod
    def get_search_field_defs(cls):
        return [
            cls.get_search_field_defs_with_key(None),
            Client.get_search_field_defs_with_key("client"),
            Vehicle.get_search_field_defs_with_key("vehicle")
        ]

    def get_total_cost(self):
        return (
            ServiceHistory.objects
                .filter(repair_order=self)
                .aggregate(total_cost=Sum('service__price'))['total_cost'] or 0
        )

    card_icon = "car"
    def card_title(self):
        return f"№{self.id}: {self.vehicle}"
    def card_tags(self):
        result = {}
        if self.finish_date:
            if self.is_cancelled:
                result.update({ "Отменен": "secondary" })
            else:
                result.update({ f"Завершен {self.finish_date.strftime(datetime_format)}": "secondary" })
                if self.finish_until and self.finish_until < self.finish_date:
                    result.update({ f"Просрочен": "danger" })
                if not self.is_paid:
                    result.update({ "Не оплачен": "primary" })
                elif self.is_warranty:
                    result.update({ "Гарантийный": "primary" })
        elif self.finish_until:
            result.update({
                f"Завершить до: {self.finish_until.strftime(datetime_format)}":
                    "secondary" if self.finish_until > timezone.now().date()
                    else "warning" if self.finish_until == timezone.now().date()
                    else "danger"
            })
        else:
            result.update({ f"Создана: {self.start_date.strftime(datetime_format)}": "secondary" })
        if self.comments:
            result.update({f"Комментарий: {self.comments}": "black"})

        return result
    def card_subtitle(self):
        return f"Клиент: {self.client}"
    def card_subtitle_extra(self):
        return f"Мастер: {self.master}"
FullTextSearchMixin.initialize_search(RepairOrder)


class WarehouseProvider(FullTextSearchMixin, SoftDeleteObject, models.Model):
    morphed_name = "поставщика"
    def get_absolute_url(self):
        return reverse("provider", kwargs={"pk": self.pk})

    name = models.CharField("Название", max_length=50)
    contact_info = models.CharField("Контактная информация", max_length=150)

    create_allowed_to = [Employee.Position.WarehouseManager]
    edit_allowed_to = [Employee.Position.WarehouseManager]

    card_icon = "truck"
    def card_title(self):
        return self.name
    def card_subtitle(self):
        return self.contact_info

    def __str__(self):
        return f"{self.name} ({self.contact_info})"
FullTextSearchMixin.initialize_search(WarehouseProvider)


class WarehouseItem(FullTextSearchMixin, SoftDeleteObject, models.Model):
    morphed_name = "расходника"
    def get_absolute_url(self):
        return reverse("item", kwargs={"pk": self.pk})

    name = models.CharField("Наименование", max_length=50)
    type = models.CharField("Тип", max_length=50)
    price = models.DecimalField("Цена", max_digits=7, decimal_places=2, validators=[MinValueValidator(0)])

    create_allowed_to = [Employee.Position.WarehouseManager]
    edit_allowed_to = [Employee.Position.WarehouseManager]

    card_icon = "gears"
    def card_title(self):
        return f"{self.name} ({self.price} руб.)"
    def card_tags(self):
        return {f"{self.get_count()} шт.": "secondary"}
    def card_subtitle(self):
        return self.type

    def get_count(self, exclude = None):
        return (
            WarehouseRestock.objects
                .filter(item=self)
                .exclude(id = exclude.id if isinstance(exclude, WarehouseRestock) else 0)
                .aggregate(total_quantity=Sum('amount'))['total_quantity'] or 0
        ) - (
            WarehouseUse.objects
                .filter(item=self)
                .exclude(id = exclude.id if isinstance(exclude, WarehouseUse) else 0)
                .aggregate(total_quantity=Sum('amount'))['total_quantity'] or 0
        )

    def __str__(self):
        return f"{self.type} {self.name}" + (f" ({self.get_count()} шт.)" if not self.deleted_at else "")
FullTextSearchMixin.initialize_search(WarehouseItem)


class WarehouseRestock(models.Model):
    morphed_name = "пополнения расходника"

    def get_absolute_url(self):
        return reverse("restock", kwargs={"item": self.item.id, "pk": self.pk})

    item = models.ForeignKey(WarehouseItem, on_delete=models.DO_NOTHING, verbose_name="Расходник")
    provider = models.ForeignKey(WarehouseProvider, on_delete=models.DO_NOTHING, verbose_name="Поставщик")
    amount = models.IntegerField("Количество", validators=[MinValueValidator(1)])

    create_allowed_to = [Employee.Position.WarehouseManager]
    edit_allowed_to = [Employee.Position.WarehouseManager]

    card_icon = "box"
    def card_title(self):
        return f"{self.amount} шт."
    def card_subtitle(self):
        return self.provider.name
    def card_clickable(self):
        return self.provider.deleted_at is None

    def clean(self):
        validate_item_count(self, self.item, "amount")

class WarehouseUse(models.Model):
    morphed_name = "использованного расходника"

    def get_absolute_url(self):
        return reverse("warehouse_use", kwargs={"order": self.repair_order.id, "pk": self.pk})

    repair_order = models.ForeignKey(RepairOrder, on_delete=models.DO_NOTHING, verbose_name="Заявка на ремонт")
    item = models.ForeignKey(WarehouseItem, on_delete=models.DO_NOTHING, verbose_name="Расходник")
    amount = models.IntegerField("Количество", validators=[MinValueValidator(1)])

    create_allowed_to = [Employee.Position.Mechanic]
    edit_allowed_to = [Employee.Position.Mechanic]

    card_icon = "toolbox"
    def card_title(self):
        return self.item
    def card_subtitle(self):
        return f"Использовано: {self.amount} шт."
    def card_clickable(self):
        return self.item.deleted_at is None

    def clean(self):
        validate_item_count(self, self.item, "amount", True)

class ServiceHistory(models.Model):
    morphed_name = "выполненной услуги"

    def get_absolute_url(self):
        return reverse("service_history", kwargs={"order": self.repair_order.id, "pk": self.pk})

    repair_order = models.ForeignKey(RepairOrder, on_delete=models.DO_NOTHING, verbose_name="Заявка на ремонт")
    service = models.ForeignKey(Service, on_delete=models.DO_NOTHING, verbose_name="Услуга")

    finish_date = models.DateField("Дата выполнения", blank=True, null=True)
    comments = models.CharField("Комментарии", max_length=300, blank=True)

    create_allowed_to = [Employee.Position.ServiceManager]
    edit_allowed_to = [Employee.Position.ServiceManager, Employee.Position.Mechanic]

    def clean(self):
        if self.finish_date and self.finish_date < self.repair_order.start_date:
            raise ValidationError({
                "finish_date": f"Дата выполнения услуги не может раньше даты заявки: {self.repair_order.start_date.strftime(datetime_format)}.",
            })

    card_icon = "wrench"
    def card_title(self):
        return self.service
    def card_subtitle(self):
        result = f"Не выполнено" if self.finish_date == None else f"Выполнено {self.finish_date.strftime(datetime_format)}"
        if self.comments:
            result += ". Комментарий: " + self.comments
        return result
    def card_clickable(self):
        return self.service.deleted_at is None
