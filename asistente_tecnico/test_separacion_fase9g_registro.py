"""Fase 9G: las rutas comerciales históricas siguen cerradas."""
from django.test import SimpleTestCase
from django.urls import reverse
from asistente_tecnico import views


class SeparacionRegistroSuscripcionesTests(SimpleTestCase):
    def test_registro_digital_retirado(self):
        self.assertFalse(hasattr(views, "digital_registro_view"))
        response = self.client.get(reverse("asistente_tecnico:digital_registro"))
        self.assertEqual(response.status_code, 410)

    def test_acceso_suscripcion_retirado(self):
        self.assertFalse(hasattr(views, "digital_acceso_view"))
        response = self.client.get(reverse("asistente_tecnico:digital_acceso"))
        self.assertEqual(response.status_code, 410)

    def test_catalogo_planes_antiguo_retirado(self):
        self.assertFalse(hasattr(views, "_planes_digitales"))
        self.assertFalse(hasattr(views, "_plan_digital"))
