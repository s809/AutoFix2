from django.urls import path
from . import views

urlpatterns = [
    path('', views.HomePageView, name='home'),

    path('repair/', views.RedirectUpView),

    path('repair/orders/', views.RepairOrderListView.as_view(), name='orders'),
    path('repair/orders/create/', views.RepairOrderCreateView.as_view(), name='order_create'),
    path('repair/orders/<int:pk>/', views.RepairOrderUpdateView.as_view(), name='order'),
    path('repair/orders/<int:pk>/receipt/', views.RepairOrderReceiptView.as_view(), name='order_receipt'),
    path('repair/orders/<int:order>/history/', views.RedirectUpView),
    path('repair/orders/<int:order>/history/create/', views.ServiceHistoryCreateView.as_view(), name='service_history_create'),
    path('repair/orders/<int:order>/history/<int:pk>/', views.ServiceHistoryUpdateView.as_view(), name='service_history'),
    path('repair/orders/<int:order>/warehouse_uses/', views.RedirectUpView),
    path('repair/orders/<int:order>/warehouse_uses/create/', views.WarehouseUseCreateView.as_view(), name='warehouse_use_create'),
    path('repair/orders/<int:order>/warehouse_uses/<int:pk>/', views.WarehouseUseUpdateView.as_view(), name='warehouse_use'),

    path('repair/services/', views.ServiceListView.as_view(), name='services'),
    path('repair/services/create/', views.ServiceCreateView.as_view(), name='service_create'),
    path('repair/services/<int:pk>/', views.ServiceUpdateView.as_view(), name='service'),

    path('repair/clients/', views.ClientListView.as_view(), name='clients'),
    path('repair/clients/create/', views.ClientCreateView.as_view(), name='client_create'),
    path('repair/clients/<int:pk>/', views.ClientUpdateView.as_view(), name='client'),

    path('repair/vehicles/', views.VehicleListView.as_view(), name='vehicles'),
    path('repair/vehicles/create/', views.VehicleCreateView.as_view(), name='vehicle_create'),
    path('repair/vehicles/<int:pk>/', views.VehicleUpdateView.as_view(), name='vehicle'),

    path('warehouse/items/', views.WarehouseItemListView.as_view(), name='items'),
    path('warehouse/items/create/', views.WarehouseItemCreateView.as_view(), name='item_create'),
    path('warehouse/items/<int:pk>/', views.WarehouseItemUpdateView.as_view(), name='item'),
    path('warehouse/items/<int:item>/restocks/', views.RedirectUpView),
    path('warehouse/items/<int:item>/restocks/create/', views.WarehouseRestockCreateView.as_view(), name='restock_create'),
    path('warehouse/items/<int:item>/restocks/<int:pk>/', views.WarehouseRestockUpdateView.as_view(), name='restock'),

    path('warehouse/', views.RedirectUpView),

    path('warehouse/providers/', views.WarehouseProviderListView.as_view(), name='providers'),
    path('warehouse/providers/create/', views.WarehouseProviderCreateView.as_view(), name='provider_create'),
    path('warehouse/providers/<int:pk>/', views.WarehouseProviderUpdateView.as_view(), name='provider'),

    path('employees/', views.EmployeeListView.as_view(), name='employees'),
    path('employees/create/', views.EmployeeCreateView.as_view(), name='employee_create'),
    path('employees/<int:pk>/', views.EmployeeUpdateView.as_view(), name='employee'),
]
