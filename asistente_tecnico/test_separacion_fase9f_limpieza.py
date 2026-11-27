"""Fase 9F (segunda parte): retirar cuatro vistas administrativas comerciales sin tocar las rutas históricas."""
from django.test import SimpleTestCase
from django.urls import reverse, resolve
from . import views
from .urls import plataforma_digital_retirada


class RetiroVistasAdministrativasDigitalesTests(SimpleTestCase):
    def test_vistas_comerciales_administrativas_ya_no_existen(self):
        for nombre in (
            "digital_avisos_admin_view",
            "digital_comprobante_admin_view",
            "digital_suscripciones_admin_view",
            "digital_suscripcion_revisar_view",
        ):
            with self.subTest(nombre=nombre):
                self.assertFalse(hasattr(views, nombre))

    def test_urls_historicas_siguen_respondiendo_410(self):
        for nombre, args in (
            ("digital_avisos_admin", ()),
            ("digital_comprobante_admin", (1,)),
            ("digital_suscripciones_admin", ()),
            ("digital_suscripcion_revisar", (1,)),
        ):
            with self.subTest(nombre=nombre):
                url = reverse("asistente_tecnico:" + nombre, args=args)
                self.assertIs(resolve(url).func, plataforma_digital_retirada)
                for method in (self.client.get, self.client.post):
                    self.assertEqual(method(url).status_code, 410)

    def test_asistente_tecnico_conserva_rutas(self):
        for nombre in ("inicio", "biblioteca", "academia", "cms_admin"):
            with self.subTest(nombre=nombre):
                url = reverse("asistente_tecnico:" + nombre)
                self.assertIsNot(resolve(url).func, plataforma_digital_retirada)
