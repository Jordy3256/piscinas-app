from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class CentroInteligenciasTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="admin-inteligencias",
            password="test-pass-123",
            is_staff=True,
        )
        self.client.force_login(self.user)

    def test_centro_inteligencias_carga_para_admin(self):
        response = self.client.get(reverse("centro_inteligencias"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Centro de Inteligencias JVAQUA")
        self.assertContains(response, "AQUO Ejecutivo")
        self.assertContains(response, "Inventario y Consumo")
