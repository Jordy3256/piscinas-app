"""Regresión: las rutas del SaaS antiguo deben permanecer retiradas del ERP.

Las pruebas históricas de AQUO360 se conservan, pero ya no representan
el comportamiento esperado de las rutas retiradas (HTTP 410).
"""
from django.test import SimpleTestCase
from django.urls import reverse


class RutasDigitalesRetiradasTests(SimpleTestCase):
    """No reactivar accidentalmente endpoints antiguos ni exponer sus datos."""

    RUTAS_RETIRADAS = ('digital_sw', 'digital_push_estado', 'digital_push_suscribir', 'digital_push_cancelar', 'digital_registro', 'digital_acceso', 'digital_avisos_admin', 'digital_comprobante_admin', 'digital_suscripciones_admin', 'digital_suscripcion_revisar', 'digital_inicio', 'digital_centro_aquo', 'digital_academia_portal', 'digital_resolver', 'digital_aquo_conversaciones_api', 'digital_aquo_chat_api', 'digital_aquo_resultado_api', 'digital_agenda', 'digital_visita_detallada', 'digital_evidencia', 'digital_cartera', 'digital_cobro_pago', 'digital_piscinas', 'digital_piscina_detalle', 'digital_soporte', 'digital_soporte_burbuja_api', 'digital_soporte_mensajes_api', 'digital_soporte_chat', 'digital_sugerencias', 'digital_piscina_nueva', 'digital_piscina_editar', 'digital_plan_mantenimiento', 'digital_registrar_mantenimiento', 'digital_notificaciones', 'digital_notificacion_leer', 'digital_notificaciones_leer_todas', 'digital_notificacion_eliminar', 'digital_notificaciones_eliminar_todas', 'soporte_admin_lista', 'soporte_admin_burbuja_api', 'soporte_admin_mensajes_api', 'soporte_admin_chat')
    RUTAS_CON_PK = {"digital_comprobante_admin", "digital_suscripcion_revisar",
                    "digital_visita_detallada", "digital_evidencia", "digital_cobro_pago",
                    "digital_piscina_detalle", "digital_soporte_mensajes_api",
                    "digital_soporte_chat", "digital_piscina_editar",
                    "digital_plan_mantenimiento", "digital_registrar_mantenimiento",
                    "digital_notificacion_leer", "digital_notificacion_eliminar",
                    "soporte_admin_mensajes_api", "soporte_admin_chat"}

    def test_rutas_antiguas_devuelven_410_para_get_y_post(self):
        for nombre in self.RUTAS_RETIRADAS:
            kwargs = {"pk": 1} if nombre in self.RUTAS_CON_PK else {}
            url = reverse(f"asistente_tecnico:{nombre}", kwargs=kwargs)
            for metodo in ("get", "post"):
                with self.subTest(ruta=nombre, metodo=metodo):
                    respuesta = getattr(self.client, metodo)(url)
                    self.assertEqual(respuesta.status_code, 410)
                    self.assertEqual(respuesta["Cache-Control"], "private, no-store")
                    self.assertNotIn("application/json", respuesta.get("Content-Type", ""))


from django.contrib.auth import get_user_model
from django.test import TestCase


class RutasRetiradasConSesionTests(TestCase):
    """Un usuario autenticado, incluso administrador, no reabre el SaaS retirado."""

    @classmethod
    def setUpTestData(cls):
        Usuario = get_user_model()
        cls.usuario = Usuario.objects.create_user(
            username="test_legacy_usuario", password="clave-de-prueba-segura"
        )
        cls.administrador = Usuario.objects.create_superuser(
            username="test_legacy_admin",
            email="legacy-admin@example.invalid",
            password="clave-de-prueba-segura",
        )

    def test_rutas_retiradas_bloqueadas_con_sesion_de_usuario_y_administrador(self):
        for usuario in (self.usuario, self.administrador):
            self.client.force_login(usuario)
            for nombre in RutasDigitalesRetiradasTests.RUTAS_RETIRADAS:
                kwargs = (
                    {"pk": 1}
                    if nombre in RutasDigitalesRetiradasTests.RUTAS_CON_PK
                    else {}
                )
                url = reverse(f"asistente_tecnico:{nombre}", kwargs=kwargs)
                for metodo in ("get", "post"):
                    with self.subTest(rol="admin" if usuario.is_superuser else "usuario", ruta=nombre, metodo=metodo):
                        respuesta = getattr(self.client, metodo)(url)
                        self.assertEqual(respuesta.status_code, 410)
                        self.assertEqual(respuesta["Cache-Control"], "private, no-store")
            self.client.logout()
