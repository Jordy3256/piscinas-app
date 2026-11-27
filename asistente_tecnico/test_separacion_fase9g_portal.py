"""Fase 9G.2: retirada segura de vistas del portal comercial antiguo."""
from django.test import SimpleTestCase
from django.urls import reverse, resolve
from asistente_tecnico import views


class PortalDigitalRetiradoTests(SimpleTestCase):
    def test_vistas_comerciales_antiguas_eliminadas(self):
        for nombre in (
            "digital_inicio_view",
            "digital_academia_portal_view",
            "_digital_centro_aquo_legacy_view",
        ):
            with self.subTest(nombre=nombre):
                self.assertFalse(hasattr(views, nombre))

    def test_rutas_antiguas_siguen_desactivadas(self):
        for nombre in ("digital_inicio", "digital_academia_portal"):
            with self.subTest(nombre=nombre):
                ruta = reverse("asistente_tecnico:" + nombre)
                respuesta = self.client.get(ruta)
                self.assertEqual(respuesta.status_code, 410)

    def test_rutas_no_apuntan_a_vistas_eliminadas(self):
        for nombre in ("digital_inicio", "digital_academia_portal"):
            with self.subTest(nombre=nombre):
                ruta = reverse("asistente_tecnico:" + nombre)
                self.assertEqual(resolve(ruta).func.__name__, "plataforma_digital_retirada")
