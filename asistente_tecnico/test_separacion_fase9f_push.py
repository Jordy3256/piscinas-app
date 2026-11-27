"""Fase 9F: limpieza de push y Service Worker de la plataforma AQUO360 retirada."""
from django.test import SimpleTestCase
from django.urls import reverse, resolve
from . import views
from .urls import plataforma_digital_retirada


class LimpiezaPushAquo360Tests(SimpleTestCase):
    def test_vistas_push_antiguas_retiradas(self):
        for nombre in (
            "digital_push_estado_view", "digital_push_suscribir_view",
            "digital_push_cancelar_view", "digital_sw_view",
        ):
            with self.subTest(nombre=nombre):
                self.assertFalse(hasattr(views, nombre))

    def test_rutas_historicas_push_devuelven_410(self):
        for nombre in ("digital_push_estado", "digital_push_suscribir", "digital_push_cancelar", "digital_sw"):
            with self.subTest(nombre=nombre):
                url = reverse("asistente_tecnico:" + nombre)
                self.assertIs(resolve(url).func, plataforma_digital_retirada)
                self.assertEqual(self.client.get(url).status_code, 410)
                self.assertEqual(self.client.post(url).status_code, 410)

    def test_rutas_tecnicas_conservadas(self):
        for nombre in ("inicio", "biblioteca", "academia", "cms_admin"):
            with self.subTest(nombre=nombre):
                url = reverse("asistente_tecnico:" + nombre)
                self.assertIsNot(resolve(url).func, plataforma_digital_retirada)
