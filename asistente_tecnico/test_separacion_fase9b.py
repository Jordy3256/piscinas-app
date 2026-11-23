"""Pruebas de retirada segura de rutas SaaS antiguas."""
from django.test import SimpleTestCase
from django.urls import resolve, reverse
from .urls import plataforma_digital_retirada


class SeparacionFase9BTests(SimpleTestCase):
    def test_rutas_digitales_inhabilitadas(self):
        for name in (
            "digital_inicio", "digital_registro", "digital_acceso",
            "digital_piscinas", "digital_agenda", "digital_cartera",
            "digital_suscripciones_admin", "digital_notificaciones",
        ):
            with self.subTest(name=name):
                url = reverse("asistente_tecnico:" + name)
                self.assertIs(resolve(url).func, plataforma_digital_retirada)
                respuesta = self.client.get(url)
                self.assertEqual(respuesta.status_code, 410)
                self.assertIn("no-store", respuesta["Cache-Control"])

    def test_rutas_tecnicas_siguen_habilitadas(self):
        for name in ("inicio", "biblioteca", "academia", "cms_admin"):
            with self.subTest(name=name):
                self.assertIsNot(resolve(reverse("asistente_tecnico:" + name)).func,
                                 plataforma_digital_retirada)
