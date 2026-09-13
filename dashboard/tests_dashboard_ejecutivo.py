from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class DashboardEjecutivoTests(TestCase):
    def test_admin_puede_abrir_dashboard_y_salud(self):
        admin = User.objects.create_user(
            username="admin_exec",
            password="test12345",
            is_staff=True,
            is_superuser=True,
        )
        self.client.force_login(admin)
        respuesta_salud = self.client.get(reverse("salud_erp"))
        self.assertEqual(respuesta_salud.status_code, 200)
