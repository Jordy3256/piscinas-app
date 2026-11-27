"""Fase 9F: retirar vistas comerciales de cartera y notificaciones AQUO360."""
from django.test import SimpleTestCase
from django.urls import resolve, reverse
from . import views
from .urls import plataforma_digital_retirada


class LimpiezaCarteraNotificacionesDigitalesTests(SimpleTestCase):
    def test_vistas_antiguas_retiradas(self):
        for nombre in (
            "digital_notificaciones_view", "digital_notificacion_leer_view",
            "digital_notificaciones_leer_todas_view", "digital_notificacion_eliminar_view",
            "digital_notificaciones_eliminar_todas_view", "digital_cartera_view",
            "digital_cobro_pago_view",
        ):
            with self.subTest(nombre=nombre):
                self.assertFalse(hasattr(views, nombre))

    def test_rutas_historicas_siguen_bloqueadas_get_y_post(self):
        for nombre, args in (
            ("digital_notificaciones", ()), ("digital_notificacion_leer", (1,)),
            ("digital_notificaciones_leer_todas", ()),
            ("digital_notificacion_eliminar", (1,)),
            ("digital_notificaciones_eliminar_todas", ()),
            ("digital_cartera", ()), ("digital_cobro_pago", (1,)),
        ):
            with self.subTest(nombre=nombre):
                url = reverse("asistente_tecnico:" + nombre, args=args)
                self.assertIs(resolve(url).func, plataforma_digital_retirada)
                self.assertEqual(self.client.get(url).status_code, 410)
                self.assertEqual(self.client.post(url).status_code, 410)

    def test_rutas_tecnicas_siguen_disponibles(self):
        for nombre in ("inicio", "biblioteca", "academia", "cms_admin"):
            with self.subTest(nombre=nombre):
                self.assertIsNot(
                    resolve(reverse("asistente_tecnico:" + nombre)).func,
                    plataforma_digital_retirada,
                )
