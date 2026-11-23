"""Regresión de Fase 9E: soporte comercial AQUO360 retirado del ERP."""
from django.test import SimpleTestCase
from django.urls import resolve, reverse
from django.template.loader import get_template


class SeparacionSoporteDigitalFase9ETests(SimpleTestCase):
    def test_rutas_administrativas_antiguas_devuelven_410(self):
        nombres = (
            ("soporte_admin_lista", []),
            ("soporte_admin_burbuja_api", []),
            ("soporte_admin_mensajes_api", [1]),
            ("soporte_admin_chat", [1]),
        )
        for nombre, args in nombres:
            with self.subTest(nombre=nombre):
                ruta = reverse("asistente_tecnico:" + nombre, args=args)
                respuesta = self.client.get(ruta)
                self.assertEqual(respuesta.status_code, 410)

    def test_rutas_del_soporte_actual_de_clientes_siguen_registradas(self):
        for nombre in ("soporte_admin_lista", "soporte_admin_contadores"):
            with self.subTest(nombre=nombre):
                ruta = reverse(nombre)
                self.assertTrue(resolve(ruta).func)

    def test_plantillas_principales_se_pueden_cargar(self):
        get_template("dashboard/base_admin.html")
        get_template("asistente_tecnico/admin.html")
