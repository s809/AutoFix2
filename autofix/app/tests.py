from django.test import TestCase, Client
from .models import Employee


class HeaderTextTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = Employee.objects.create(
            last_name = "Петров",
            first_name = "Сергей",
            patronymic = "Морозович",
            position = Employee.Position.Administrator
        )
        self.client.force_login(self.user)

    def test_header_text(self):
        response = self.client.get("/", follow=True)
        self.assertRegexpMatches(response.rendered_content,
                                 f"{self.user.get_position_display()}\s+{self.user.last_name}\s+{self.user.first_name}\s+{self.user.patronymic}")
        pass
