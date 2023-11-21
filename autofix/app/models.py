from django.db import models
from django.db.models import Sum
from django.contrib.auth.models import *
from django.core.validators import MaxValueValidator, MinValueValidator
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
            {name: f"Недостаточно предметов. Требуется еще {-new_total_quantity} шт. предмета, имеется: {total_quantity} шт."}
        )

class Employee(AbstractUser):
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
        return self.fullName()
    def card_subtitle(self):
        return self.get_position_display() + self.end_date_reason()

    def fullName(self):
        return f"{self.last_name} {self.first_name} {self.patronymic}"
    def end_date_reason(self):
        if not self.end_date:
            return ""
        result = "уволен " + self.end_date.strftime(datetime_format)
        if self.end_reason:
            result += ". Причина: " + self.end_reason
        return f" ({result})"

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
        return self.fullName() + self.end_date_reason()

class Service(SoftDeleteObject, models.Model):
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


class RepairOrder(SoftDeleteObject, models.Model):
    morphed_name = "заявки"
    def get_absolute_url(self):
        return reverse("order", kwargs={"pk": self.pk})

    master = models.ForeignKey(Employee, on_delete=models.DO_NOTHING, limit_choices_to={"position": Employee.Position.Mechanic, "end_date__isnull": True}, verbose_name="Мастер")
    clientName = models.CharField("Имя клиента", max_length=50)
    clientPhoneNumber = PhoneNumberField("Номер телефона клиента", region="RU")

    vehicleManufacturer = models.CharField("Производитель автомобиля", max_length=50)
    vehicleModel = models.CharField("Модель автомобиля", max_length=50)
    vehicleYear = models.IntegerField("Год выпуска автомобиля", validators=[MinValueValidator(1900), MaxValueValidator(2100)])

    startDate = models.DateField("Дата записи", default=timezone.now)
    finishDate = models.DateField("Дата завершения", blank=True, null=True)
    isCancelled = models.BooleanField("Отменена")

    comments = models.CharField("Комментарии", max_length=300, blank=True)

    isPaid = models.BooleanField("Оплачено", default=False)

    create_allowed_to = [Employee.Position.ServiceManager]
    edit_allowed_to = [Employee.Position.ServiceManager,
                       Employee.Position.Mechanic,
                       Employee.Position.Cashier]

    def clean(self):
        if self.isCancelled and not self.finishDate:
            raise ValidationError({
                "isCancelled": "Для отмены заявки на ремонт требуется дата завершения."
            })
        if self.finishDate and self.finishDate < self.startDate:
            raise ValidationError({
                "finishDate": "Дата завершения заявки на ремонт не может раньше даты начала.",
            })

    def get_total_cost(self):
        return (
            ServiceHistory.objects
                .filter(repair_order=self)
                .aggregate(total_cost=Sum('service__price'))['total_cost'] or 0
        )

    card_icon = "car"
    def card_title(self):
        result = f"{self.vehicleManufacturer} {self.vehicleModel} {self.vehicleYear} г."
        if self.finishDate:
            if self.isCancelled:
                result += " (Отменено)"
            elif not self.isPaid:
                result += " (Не оплачено)"
            else:
                result += f" (Завершено {self.finishDate.strftime(datetime_format)})"
        if self.comments:
            result += f" ({self.comments})"
        return result
    def card_subtitle(self):
        return f"Клиент: {self.clientName}"
    def card_subtitle_extra(self):
        return f"Мастер: {self.master}"

# Warehouse

class WarehouseProvider(SoftDeleteObject, models.Model):
    morphed_name = "поставщика"
    def get_absolute_url(self):
        return reverse("provider", kwargs={"pk": self.pk})

    name = models.CharField("Название", max_length=50)
    contactInfo = models.CharField("Контактная информация", max_length=150)

    create_allowed_to = [Employee.Position.WarehouseManager]
    edit_allowed_to = [Employee.Position.WarehouseManager]

    card_icon = "truck"
    def card_title(self):
        return self.name
    def card_subtitle(self):
        return self.contactInfo

    def __str__(self):
        return f"{self.name} ({self.contactInfo})"


class WarehouseItem(SoftDeleteObject, models.Model):
    morphed_name = "предмета"
    def get_absolute_url(self):
        return reverse("item", kwargs={"pk": self.pk})

    name = models.CharField("Наименование", max_length=50)
    type = models.CharField("Тип", max_length=50)
    price = models.DecimalField("Цена", max_digits=7, decimal_places=2, validators=[MinValueValidator(0)])

    create_allowed_to = [Employee.Position.WarehouseManager]
    edit_allowed_to = [Employee.Position.WarehouseManager]

    card_icon = "gears"
    def card_title(self):
        return f"{self.name} ({self.price} руб.) ({self.get_count()} шт.)"
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


class WarehouseRestock(SoftDeleteObject, models.Model):
    morphed_name = "пополнения предмета"

    def get_absolute_url(self):
        return reverse("restock", kwargs={"item": self.item.id, "pk": self.pk})

    item = models.ForeignKey(WarehouseItem, on_delete=models.CASCADE, verbose_name="Предмет")
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

class WarehouseUse(SoftDeleteObject, models.Model):
    morphed_name = "использованного предмета"

    def get_absolute_url(self):
        return reverse("warehouse_use", kwargs={"order": self.repair_order.id, "pk": self.pk})

    repair_order = models.ForeignKey(RepairOrder, on_delete=models.CASCADE, verbose_name="Заявка на ремонт")
    item = models.ForeignKey(WarehouseItem, on_delete=models.DO_NOTHING, verbose_name="Предмет")
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


# Service

class ServiceHistory(SoftDeleteObject, models.Model):
    morphed_name = "выполненной услуги"

    def get_absolute_url(self):
        return reverse("service_history", kwargs={"order": self.repair_order.id, "pk": self.pk})

    repair_order = models.ForeignKey(RepairOrder, on_delete=models.CASCADE, verbose_name="Заявка на ремонт")
    service = models.ForeignKey(Service, on_delete=models.DO_NOTHING, verbose_name="Услуга")

    finishDate = models.DateField("Дата выполнения", blank=True, null=True)
    comments = models.CharField("Комментарии", max_length=300, blank=True)

    create_allowed_to = [Employee.Position.ServiceManager]
    edit_allowed_to = [Employee.Position.ServiceManager, Employee.Position.Mechanic]

    def clean(self):
        if self.finishDate and self.finishDate < self.repair_order.startDate:
            raise ValidationError({
                "finishDate": f"Дата выполнения услуги не может раньше даты заявки: {self.repair_order.startDate.strftime(datetime_format)}.",
            })

    card_icon = "wrench"
    def card_title(self):
        return self.service
    def card_subtitle(self):
        result = f"Не выполнено" if self.finishDate == None else f"Выполнено {self.finishDate.strftime(datetime_format)}"
        if self.comments:
            result += ". Комментарий: " + self.comments
        return result
    def card_clickable(self):
        return self.service.deleted_at is None
