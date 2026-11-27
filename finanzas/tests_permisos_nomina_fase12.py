"""Pruebas negativas de permisos de nómina (Fase 12).

No modifica datos productivos; Django crea una base temporal de pruebas.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class PermisosNominaFase12Tests(TestCase):
    """Un usuario sin privilegios no puede consultar ni mutar nómina."""

    def setUp(self):
        self.usuario = get_user_model().objects.create_user(
            username="usuario_sin_permisos_nomina", password="prueba_segura_123"
        )
        self.client.force_login(self.usuario)

    def _rutas_administrativas(self):
        return (
            ("finanzas_nomina", (), "get"),
            ("finanzas_nomina_generar", (), "post"),
            ("finanzas_trabajador_configuracion_pago", (999999,), "get"),
            ("finanzas_trabajador_configuracion_pago", (999999,), "post"),
            ("finanzas_nomina_pago_consolidado", (999999,), "get"),
            ("finanzas_nomina_pago_consolidado", (999999,), "post"),
            ("finanzas_nomina_detalle", (999999,), "get"),
            ("finanzas_nomina_pago_nuevo", (999999,), "post"),
            ("finanzas_nomina_pago_anular", (999999, 999999), "post"),
            ("finanzas_nomina_mensual_pdf", (), "get"),
            ("finanzas_pago_trabajador_comprobante_pdf", (999999,), "get"),
        )

    def test_usuario_no_administrador_denegado_en_todas_las_rutas(self):
        for nombre, argumentos, metodo in self._rutas_administrativas():
            with self.subTest(ruta=nombre, metodo=metodo):
                url = reverse(nombre, args=argumentos)
                respuesta = getattr(self.client, metodo)(url)
                self.assertEqual(respuesta.status_code, 403)

    def test_anonimo_no_puede_acceder_a_nomina(self):
        self.client.logout()
        for nombre, argumentos, metodo in self._rutas_administrativas():
            with self.subTest(ruta=nombre, metodo=metodo):
                url = reverse(nombre, args=argumentos)
                respuesta = getattr(self.client, metodo)(url)
                self.assertNotEqual(respuesta.status_code, 200)
                self.assertNotEqual(respuesta.status_code, 500)

    def test_usuario_no_administrador_no_puede_descargar_nomina_ajena(self):
        url = reverse("finanzas_nomina_trabajador_pdf", args=(999999,))
        respuesta = self.client.get(url)
        self.assertEqual(respuesta.status_code, 403)
