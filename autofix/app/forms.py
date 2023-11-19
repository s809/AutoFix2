from typing import Any
from django.core.files.base import File
from django.db.models.base import Model
from django.forms import *
from django.contrib.auth.forms import *
from django.forms.utils import ErrorList
from .models import *
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Column, Submit, HTML, Field


class Column(Column):
    css_class = "d-flex"


submit_button = Submit("submit", "Сохранить", css_class="btn-primary ml-2")
delete_button = HTML("""
    <a class="btn btn-danger ms-2" href="?delete">Удалить</a>
""")

def button_column(form: ModelForm, kwargs: dict):
    position = kwargs["initial"]["position"]
    return Column(submit_button, delete_button) if form.instance.pk is not None and position in [Employee.Position.Administrator, *form.instance.create_allowed_to] \
        else submit_button if position in [Employee.Position.Administrator, *form.instance.edit_allowed_to] \
        else None

def restrict_form_fields(form: ModelForm, kwargs: dict, fields_by_permission: list[list[str]]):
    position = kwargs["initial"]["position"]

    if position not in [Employee.Position.Administrator, *form.instance.edit_allowed_to]:
        for field in form.fields.values():
            field.disabled = True
        return

    for allowed_positions, fields in fields_by_permission:
        for field in fields:
            form.fields[field].disabled = True

    for allowed_positions, fields in fields_by_permission:
        if position in [Employee.Position.Administrator, *allowed_positions]:
            for field in fields:
                form.fields[field].disabled = False

class BaseForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        restrict_form_fields(self, kwargs, [])

        self.helper = FormHelper(self)
        self.helper.layout.fields.append(button_column(self, kwargs))

class ServiceForm(BaseForm):
    class Meta:
        model = Service
        exclude = []

class ServiceHistoryForm(BaseForm):
    class Meta:
        model = ServiceHistory
        exclude = ["repair_order"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        restrict_form_fields(self, kwargs, [
            [[Employee.Position.ServiceManager], ['service']]
        ])

        self.helper = FormHelper()
        self.helper.layout = Layout(
            'service',
            Fieldset(
                'Выполнение',
                Column('finishDate'),
                'comments',
            ),
            button_column(self, kwargs)
        )

    def clean(self) -> dict[str, Any]:
        self.instance.repair_order_id = self.initial["order"]
        return super().clean()

class WarehouseUseForm(BaseForm):
    class Meta:
        model = WarehouseUse
        exclude = ["repair_order"]
    def clean(self) -> dict[str, Any]:
        self.instance.repair_order_id = self.initial["order"]
        return super().clean()

class WarehouseRestockForm(BaseForm):
    class Meta:
        model = WarehouseRestock
        exclude = ["item"]

    def clean(self) -> dict[str, Any]:
        self.instance.item_id = self.initial["item"]
        return super().clean()

class WarehouseItemForm(BaseForm):
    class Meta:
        model = WarehouseItem
        exclude = []

class WarehouseProviderForm(BaseForm):
    class Meta:
        model = WarehouseProvider
        exclude = []

class BaseEmployeeForm():
    class Meta:
        model = Employee
        fields = ('first_name', 'last_name', 'patronymic',
                  'passport_info',
                  'position',
                  'date_joined', 'end_date', 'end_reason',
                  'username')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.layout = Layout(
            Column('first_name', 'last_name', 'patronymic'),
            'passport_info',
            'position',
            Column('date_joined', *(['end_date', 'end_reason'] if kwargs["instance"] else [])),
            Column('username', *(['password'] if kwargs["instance"] else ['password1', 'password2'])),
            submit_button
        )

class EmployeeCreationForm(BaseEmployeeForm, UserCreationForm):
    class Meta(BaseEmployeeForm.Meta, UserCreationForm.Meta):
        fields = BaseEmployeeForm.Meta.fields + ('password1', 'password2')

class EmployeeChangeForm(BaseEmployeeForm, UserChangeForm):
    class Meta(BaseEmployeeForm.Meta, UserChangeForm.Meta):
        pass

    password = CharField(
        label="Пароль",
        help_text="Оставьте пустым, чтобы оставить без изменений.",
        widget=PasswordInput(),
        required=False)

    def save(self, commit: bool = ...) -> Any:
        instance: Employee = super().save(commit)
        if self.cleaned_data["password"]:
            instance.set_password(self.cleaned_data["password"])
        instance.save()
        return instance

class RepairOrderForm(ModelForm):
    class Meta:
        model = RepairOrder
        fields = ('master',
            'clientName', 'clientPhoneNumber',
            'vehicleManufacturer', 'vehicleModel', 'vehicleYear',
            'startDate', 'finishDate', 'isCancelled',
            'comments',
            'isPaid')

    totalCost = DecimalField(
        label="Итого к оплате",
        required=False,
        widget=NumberInput(attrs={"readonly": "", "step": "0.01"}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **(kwargs | {"initial": {
            "totalCost": '{0:.2f}'.format(kwargs["instance"].get_total_cost() if kwargs["instance"] else 0)
        }}))

        restrict_form_fields(self, kwargs, [
            [[Employee.Position.ServiceManager],
                ['master',
                'clientName', 'clientPhoneNumber',
                'vehicleManufacturer', 'vehicleModel', 'vehicleYear',
                'startDate', 'isCancelled']],
            [[Employee.Position.ServiceManager,
              Employee.Position.Mechanic], ["finishDate"]],
            [[Employee.Position.Cashier], ["isPaid"]]
        ])

        self.helper = FormHelper()
        self.helper.layout = Layout(
            'master',
            Fieldset(
                'Клиент',
                Column('clientName', 'clientPhoneNumber')
            ),
            Fieldset(
                'Автомобиль',
                Column('vehicleManufacturer', 'vehicleModel', 'vehicleYear')
            ),
            Fieldset(
                'Заявка',
                Column('startDate', 'finishDate' if kwargs["instance"] else None),
                *([
                    'isCancelled',
                    'comments'
                ] if kwargs["instance"] else []),
            ),
            *([Fieldset(
                'Оплата',
                Column('totalCost'),
                'isPaid'
            )] if kwargs["instance"] else []),
            button_column(self, kwargs)
        )
