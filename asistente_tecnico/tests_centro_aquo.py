from django.test import SimpleTestCase
from django.urls import reverse, resolve
from . import views
from .urls import plataforma_digital_retirada


class CentroAquoAccesoTests(SimpleTestCase):
    def test_ruta_del_centro(self):
        url = reverse("asistente_tecnico:digital_centro_aquo")
        self.assertIn("/digital/aquo/", url)
        self.assertIs(resolve(url).func, plataforma_digital_retirada)

    def test_centro_retirado(self):
        self.assertFalse(hasattr(views, "digital_centro_aquo_view"))
        url = reverse("asistente_tecnico:digital_centro_aquo")
        self.assertEqual(self.client.get(url).status_code, 410)
        self.assertEqual(self.client.post(url).status_code, 410)
