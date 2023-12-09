from django.contrib.admin.sites import AdminSite
from django.contrib.auth.admin import *
from django.contrib import admin
from django.db import models

from .forms import *
from .models import *

def list_display_fields(model: models.Model, *exclude: models.Model):
    exclude_names = [c.__name__.lower() for c in exclude]
    return [field.name for field in model._meta.get_fields() if field.name not in exclude_names]

@admin.register(Employee)
class EmployeeAdmin(UserAdmin):
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ['first_name', 'last_name'] +
            [field.name for field in Employee._meta.get_fields() if field.name not in [field.name for field in User._meta.get_fields()] + ['repairorder', 'logentry']] +
                ['username', 'password1', 'password2']
        }),
    )
    fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': [field.name for field in Employee._meta.get_fields() if field.name not in ['id', 'groups', 'user_permissions', 'repairorder', 'logentry']]
        }),
    )

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = list_display_fields(Service, ServiceHistory)

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = list_display_fields(Client, RepairOrder)

@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = list_display_fields(Vehicle, RepairOrder)

# Warehouse

class WarehouseRestockAdminInline(admin.TabularInline):
    model = WarehouseRestock

class WarehouseUseAdminInline(admin.TabularInline):
    model = WarehouseUse

@admin.register(WarehouseProvider)
class WarehouseProviderAdmin(admin.ModelAdmin):
    list_display = list_display_fields(WarehouseProvider, WarehouseRestock, WarehouseUse)

@admin.register(WarehouseItem)
class WarehouseItemAdmin(admin.ModelAdmin):
    list_display = list_display_fields(WarehouseItem, WarehouseRestock, WarehouseUse)
    inlines = (WarehouseRestockAdminInline, )


# Orders

class ServiceHistoryAdminInline(admin.TabularInline):
    model = ServiceHistory

@admin.register(RepairOrder)
class RepairOrderAdmin(admin.ModelAdmin):
    list_display = list_display_fields(RepairOrder, WarehouseUse, ServiceHistory)
    inlines = (ServiceHistoryAdminInline, WarehouseUseAdminInline)
