from datetime import timedelta
from decimal import Decimal
from django.test import TestCase
from django import test
from .models import *
from django.utils.dateparse import parse_datetime


class HeaderTextTestCase(TestCase):
    def setUp(self):
        self.client = test.Client()
        self.user = Employee.objects.create(
            last_name = "Петров",
            first_name = "Сергей",
            patronymic = "Морозович",
            position = Employee.Position.Administrator
        )
        self.client.force_login(self.user)

    def test_header_text(self):
        response = self.client.get("/", follow=True)
        self.assertInHTML(f"Администратор Петров Сергей Морозович", response.rendered_content)


class RepairOrderListFiltersTestCase(TestCase):
    def setUp(self):
        self.user1 = Employee.objects.create(
            last_name="Петров",
            first_name="Сергей",
            patronymic="Морозович",
            position=Employee.Position.Administrator,
            username="user1"
        )
        self.user2 = Employee.objects.create(
            last_name="Петров2",
            first_name="Сергей2",
            patronymic="Морозович2",
            position=Employee.Position.Mechanic,
            username="user2"
        )
        self.client.force_login(self.user1)

        repair_order_kwargs = {
            "start_date": timezone.now().date(),
            "finish_until": timezone.now().date(),
            "is_cancelled": False,
            "vehicle_mileage": 10000,
            "client": Client.objects.create(
                full_name = "full_name",
                phone_number = "+79955443322"
            ),
            "vehicle": Vehicle.objects.create(
                manufacturer="Toyota",
                model="Camry",
                year=2022,
                license_number="ABC123",
                vin="12345678901234567"
            )
        }

        self.order_user1 = RepairOrder.objects.create(
            master=self.user1,
            **repair_order_kwargs
        )
        self.order_user1_finished_unpaid = RepairOrder.objects.create(
            master=self.user1,
            finish_date=timezone.now().date(),
            **repair_order_kwargs
        )
        self.order_user1_finished = RepairOrder.objects.create(
            master=self.user1,
            finish_date=timezone.now().date(),
            is_paid=True,
            **repair_order_kwargs
        )
        self.order_user1_cancelled = RepairOrder.objects.create(
            master=self.user1,
            finish_date=timezone.now().date(),
            **repair_order_kwargs | {"is_cancelled": True}
        )
        self.order_user2 = RepairOrder.objects.create(
            master=self.user2,
            **repair_order_kwargs
        )

    def test_plain(self):
        response = self.client.get(f"/repair/orders/")
        self.assertQuerySetEqual(response.context['object_list'], [
            self.order_user1,
            self.order_user1_finished_unpaid,
            self.order_user2
        ])

    def test_master(self):
        response = self.client.get(f"/repair/orders/?filter_master={self.user1.id}")
        self.assertQuerySetEqual(response.context['object_list'], [
            self.order_user1,
            self.order_user1_finished_unpaid,
        ])

    def test_show_finished(self):
        response = self.client.get(f"/repair/orders/?show_finished=1")
        self.assertQuerySetEqual(response.context['object_list'], [
            self.order_user1,
            self.order_user1_finished_unpaid,
            self.order_user1_finished,
            self.order_user1_cancelled,
            self.order_user2
        ])

    def test_master_and_show_finished(self):
        response = self.client.get(f"/repair/orders/?filter_master={self.user1.id}&show_finished=1")
        self.assertQuerySetEqual(response.context['object_list'], [
            self.order_user1,
            self.order_user1_finished_unpaid,
            self.order_user1_finished,
            self.order_user1_cancelled,
        ])

    def test_invalid_parameters(self):
        response = self.client.get(f"/repair/orders/?filter_master=invalid&show_finished=invalid")
        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(response.context['object_list'], [
            self.order_user1,
            self.order_user1_finished_unpaid,
            self.order_user2
        ])


class EmployeeListFiltersTestCase(TestCase):
    def setUp(self):
        self.user1 = Employee.objects.create(
            last_name="Петров",
            first_name="Сергей",
            patronymic="Морозович",
            position=Employee.Position.Administrator,
            username="user1"
        )
        self.user2 = Employee.objects.create(
            last_name="Петров2",
            first_name="Сергей2",
            patronymic="Морозович2",
            position=Employee.Position.Mechanic,
            username="user2",
            end_date=timezone.now().date()
        )
        self.client.force_login(self.user1)

    def test_plain(self):
        response = self.client.get(f"/employees/")
        self.assertQuerySetEqual(response.context['object_list'], [
            self.user1
        ])

    def test_show_removed(self):
        response = self.client.get(f"/employees/?show_removed=1")
        self.assertQuerySetEqual(response.context['object_list'], [
            self.user1,
            self.user2
        ])

    def test_invalid_parameters(self):
        response = self.client.get(f"/employees/?show_removed=invalid")
        self.assertQuerySetEqual(response.context['object_list'], [
            self.user1
        ])


class RepairOrderValidationTestCase(TestCase):
    def setUp(self):
        # Set up necessary objects for testing
        self.client = Client.objects.create(full_name="Test Client")
        self.vehicle = Vehicle.objects.create(manufacturer="Toyota", model="Camry", year=2022)
        self.master = Employee.objects.create(
            last_name="Иванов",
            first_name="Иван",
            patronymic="Иванович",
            position=Employee.Position.Mechanic,
            username="mechanic1"
        )

    def test_valid_repair_order(self):
        # Test case for a valid RepairOrder
        repair_order = RepairOrder(
            master=self.master,
            client=self.client,
            vehicle=self.vehicle,
            vehicle_mileage=5000,
            start_date=timezone.now(),
            finish_until=timezone.now() + timezone.timedelta(days=2),
            is_cancelled=False,
            complaints="Some complaints",
            is_paid=False,
            is_warranty=False
        )

        # No validation errors should be raised
        repair_order.full_clean()

    def test_invalid_finish_until(self):
        # Test case for finish_until earlier than start_date
        repair_order = RepairOrder(
            master=self.master,
            client=self.client,
            vehicle=self.vehicle,
            vehicle_mileage=5000,
            start_date=timezone.now(),
            finish_until=timezone.now() - timezone.timedelta(days=2),
            is_cancelled=False,
            complaints="Some complaints",
            is_paid=False,
            is_warranty=False
        )

        # Validation error should be raised
        with self.assertRaises(ValidationError):
            repair_order.full_clean()

    def test_missing_finish_date_for_cancelled_order(self):
        # Test case for missing finish_date when order is cancelled
        repair_order = RepairOrder(
            master=self.master,
            client=self.client,
            vehicle=self.vehicle,
            vehicle_mileage=5000,
            start_date=timezone.now(),
            finish_until=timezone.now() + timezone.timedelta(days=2),
            is_cancelled=True,
            complaints="Some complaints",
            is_paid=False,
            is_warranty=False
        )

        # Validation error should be raised
        with self.assertRaises(ValidationError):
            repair_order.full_clean()

    def test_finish_date_earlier_than_start_date(self):
        # Test case for finish_date earlier than start_date
        repair_order = RepairOrder(
            master=self.master,
            client=self.client,
            vehicle=self.vehicle,
            vehicle_mileage=5000,
            start_date=timezone.now(),
            finish_until=timezone.now() + timezone.timedelta(days=2),
            finish_date=timezone.now() - timezone.timedelta(days=1),
            is_cancelled=False,
            complaints="Some complaints",
            is_paid=False,
            is_warranty=False
        )

        # Validation error should be raised
        with self.assertRaises(ValidationError):
            repair_order.full_clean()

    def test_paid_warranty_order(self):
        repair_order = RepairOrder(
            master=self.master,
            client=self.client,
            vehicle=self.vehicle,
            vehicle_mileage=5000,
            start_date=timezone.now(),
            finish_until=timezone.now() + timezone.timedelta(days=2),
            finish_date=timezone.now() + timezone.timedelta(days=1),
            is_cancelled=False,
            complaints="Some complaints",
            is_paid=False,
            is_warranty=True
        )

        # is_paid should be set when warranty repair is completed
        repair_order.full_clean()
        self.assertTrue(repair_order.is_paid)

    def test_total_cost_calculation(self):
        # Test case for calculating total cost of services associated with a repair order
        repair_order = RepairOrder(
            master=self.master,
            client=self.client,
            vehicle=self.vehicle,
            vehicle_mileage=5000,
            start_date=timezone.now(),
            finish_until=timezone.now() + timezone.timedelta(days=2),
            is_cancelled=False,
            complaints="Some complaints",
            is_paid=False,
            is_warranty=False
        )
        repair_order.save()

        # Create service history entries
        service1 = ServiceHistory.objects.create(
            repair_order=repair_order,
            service=Service.objects.create(name="Service1", price=Decimal("50.00"))
        )
        service2 = ServiceHistory.objects.create(
            repair_order=repair_order,
            service=Service.objects.create(name="Service2", price=Decimal("75.00"))
        )

        # Ensure the total cost is calculated correctly
        self.assertEqual(repair_order.get_total_cost(), Decimal("125.00"))


class EmployeeValidationTestCase(TestCase):
    def setUp(self):
        # Set up necessary objects for testing
        self.administrator = Employee.objects.create(
            first_name="John",
            last_name="Doe",
            patronymic="",
            passport_info="1234567890",
            position=Employee.Position.Administrator
        )

    def test_end_reason_without_end_date(self):
        # Test case for end_reason without end_date
        employee = Employee(
            first_name="Test",
            last_name="Employee",
            patronymic="",
            passport_info="0987654321",
            position=Employee.Position.Mechanic,
            end_reason="Found a new job"
        )

        # Validation error should be raised
        with self.assertRaises(ValidationError):
            employee.full_clean()

    def test_end_date_before_date_joined(self):
        # Test case for end_date before date_joined
        employee = Employee(
            first_name="Test",
            last_name="Employee",
            patronymic="",
            passport_info="0987654321",
            position=Employee.Position.Mechanic,
            end_date="2022-01-01"
        )

        # Validation error should be raised
        with self.assertRaises(ValidationError):
            employee.full_clean()

    def test_end_date_reason_format(self):
        # Test case for end_date_reason format
        employee = Employee(
            first_name="Test",
            last_name="Employee",
            patronymic="",
            passport_info="0987654321",
            position=Employee.Position.Mechanic,
            end_date=parse_datetime("2023-01-01").date(),
            end_reason="Retired"
        )
        expected_result = "Уволен 01.01.2023. Причина: Retired"

        # Validate the end_date_reason method
        self.assertEqual(employee.end_date_reason(parens=True), f" ({expected_result})")

    def test_clean_method(self):
        # Test case for the clean method
        employee = Employee(
            first_name="Test",
            last_name="Employee",
            patronymic="",
            passport_info="0987654321",
            position=Employee.Position.Mechanic,
            end_date = timezone.now().date(),
            end_reason="Retired"
        )

        # Set end_date and check that is_active is correctly updated
        employee.clean()
        self.assertFalse(employee.is_active)


class WarehouseUseValidationTestCase(TestCase):
    def setUp(self):
        # Set up necessary objects for testing
        self.warehouse_manager = Employee.objects.create(
            first_name="John",
            last_name="Doe",
            patronymic="",
            passport_info="1234567890",
            position=Employee.Position.WarehouseManager
        )
        self.warehouse_item = WarehouseItem.objects.create(
            name="Test Item",
            type="Test Type",
            price=10.0
        )
        self.warehouse_provider = WarehouseProvider.objects.create(
            name="Test Provider"
        )
        self.repair_order = RepairOrder.objects.create(
            master=self.warehouse_manager,
            client=Client.objects.create(full_name="Test Client"),
            vehicle=Vehicle.objects.create(model="Test Model", year=2022),
            vehicle_mileage=5000,
            start_date=timezone.now(),
            finish_until=timezone.now() + timedelta(days=7),
            is_cancelled=False,
            complaints="Test Complaints"
        )

    def test_restock_item_count_validation(self):
        # Test case for validating item count during restocking
        WarehouseRestock.objects.create(
            item=self.warehouse_item,
            provider=self.warehouse_provider,
            amount=4
        )

        # Validate the item count during restocking
        with self.assertRaises(ValidationError) as context:
            WarehouseUse(
                repair_order=self.repair_order,
                item=self.warehouse_item,
                amount=10
            ).clean()

        expected_error_message = {"amount": ["Недостаточно единиц расходника. Требуется еще 6 шт., имеется: 4 шт."]}
        self.assertEqual(context.exception.message_dict, expected_error_message)


class ServiceHistoryValidationTestCase(TestCase):
    def setUp(self):
        # Set up necessary objects for testing
        self.warehouse_manager = Employee.objects.create(
            first_name="John",
            last_name="Doe",
            patronymic="",
            passport_info="1234567890",
            position=Employee.Position.WarehouseManager
        )
        self.warehouse_item = WarehouseItem.objects.create(
            name="Test Item",
            type="Test Type",
            price=10.0
        )
        self.warehouse_provider = WarehouseProvider.objects.create(
            name="Test Provider"
        )
        self.repair_order = RepairOrder.objects.create(
            master=self.warehouse_manager,
            client=Client.objects.create(full_name="Test Client"),
            vehicle=Vehicle.objects.create(model="Test Model", year=2022),
            vehicle_mileage=5000,
            start_date=timezone.now(),
            finish_until=timezone.now() + timedelta(days=7),
            is_cancelled=False,
            complaints="Test Complaints"
        )

    def test_service_history_finish_date_validation(self):
        # Test case for validating finish date in service history
        service = Service.objects.create(name="Test Service", price=50.0)
        service_history = ServiceHistory(
            repair_order=self.repair_order,
            service=service,
            finish_date=self.repair_order.start_date - timedelta(days=1)  # Setting finish date before repair order start date
        )

        # Validate the finish date in service history
        with self.assertRaises(ValidationError) as context:
            service_history.clean()

        expected_error_message = {"finish_date": [f"Дата выполнения услуги не может раньше даты заявки: {self.repair_order.start_date.strftime(datetime_format)}."]}
        self.assertEqual(context.exception.message_dict, expected_error_message)


class PermissionCheckTestCase(TestCase):
    def setUp(self):
        self.admin_user = Employee.objects.create_user(
            username='admin',
            position=Employee.Position.Administrator
        )
        self.service_manager_user = Employee.objects.create_user(
            username='service_manager',
            position=Employee.Position.ServiceManager
        )
        self.mechanic_user = Employee.objects.create_user(
            username='mechanic',
            position=Employee.Position.Mechanic
        )
        self.warehouse_manager_user = Employee.objects.create_user(
            username='warehouse_manager',
            position=Employee.Position.WarehouseManager
        )

        self.repair_order = RepairOrder.objects.create(
            master=self.mechanic_user,
            client=Client.objects.create(full_name="Test Client"),
            vehicle=Vehicle.objects.create(model="Test Model", year=2022),
            vehicle_mileage=5000,
            start_date=timezone.now(),
            finish_until=timezone.now() + timedelta(days=7),
            is_cancelled=False,
            complaints="Test Complaints"
        )

    def test_list_check(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('orders'))
        self.assertEqual(response.status_code, 200)

        self.client.force_login(self.service_manager_user)
        response = self.client.get(reverse('orders'))
        self.assertEqual(response.status_code, 200)

        self.client.force_login(self.mechanic_user)
        response = self.client.get(reverse('orders'))
        self.assertEqual(response.status_code, 200)

        self.client.force_login(self.warehouse_manager_user)
        response = self.client.get(reverse('orders'))
        self.assertEqual(response.status_code, 302)

    def test_create_check(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('order_create'))
        self.assertEqual(response.status_code, 200)

        self.client.force_login(self.service_manager_user)
        response = self.client.get(reverse('order_create'))
        self.assertEqual(response.status_code, 200)

        self.client.force_login(self.mechanic_user)
        response = self.client.get(reverse('order_create'))
        self.assertEqual(response.status_code, 302)

        self.client.force_login(self.warehouse_manager_user)
        response = self.client.get(reverse('order_create'))
        self.assertEqual(response.status_code, 302)

    def test_update_check(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('order', args=[self.repair_order.id]))
        self.assertEqual(response.status_code, 200)

        self.client.force_login(self.service_manager_user)
        response = self.client.get(reverse('order', args=[self.repair_order.id]))
        self.assertEqual(response.status_code, 200)

        self.client.force_login(self.mechanic_user)
        response = self.client.get(reverse('order', args=[self.repair_order.id]))
        self.assertEqual(response.status_code, 200)

        self.client.force_login(self.warehouse_manager_user)
        response = self.client.get(reverse('order', args=[self.repair_order.id]))
        self.assertEqual(response.status_code, 302)
