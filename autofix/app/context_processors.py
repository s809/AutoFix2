from .models import *

def nav_urls(request):
    if not isinstance(request.user, Employee):
        return {}

    user_position = request.user.position
    position_permissions = {k: user_position in [Employee.Position.Administrator, *v] for k, v in {
        "can_view_orders": RepairOrder.edit_allowed_to,
        "can_view_services": Service.edit_allowed_to,
        "can_view_items": WarehouseItem.edit_allowed_to,
        "can_view_providers": WarehouseItem.edit_allowed_to,
        "can_view_employees": Employee.edit_allowed_to,
    }.items()}

    repair_entries = {k:v for k, v in {
        "Заявки": "orders" if position_permissions["can_view_orders"] else None,
        "Услуги": "services" if position_permissions["can_view_services"] else None
    }.items() if v is not None}
    warehouse_entries = {k:v for k, v in {
        "Предметы": "items" if position_permissions["can_view_items"] else None,
        "Поставщики": "providers" if position_permissions["can_view_providers"] else None
    }.items() if v is not None}
    extra_entries = {k:v for k, v in {
        "Сотрудники": "employees" if position_permissions["can_view_employees"] else None
    }.items() if v is not None}

    nav_urls = {k:v for k, v in {
        "Ремонт": repair_entries if len(repair_entries) else None,
        "Склад": warehouse_entries if len(warehouse_entries) else None,
        **extra_entries
    }.items() if v is not None and v}

    return {
        "nav_urls": nav_urls,
        "first_visible_entry": next(iter({**repair_entries, **warehouse_entries, **extra_entries}.values()))
    }
