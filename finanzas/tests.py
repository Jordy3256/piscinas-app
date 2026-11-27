"""Pruebas de acceso a comprobantes financieros privados."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class SeguridadComprobantesFinancierosTests(TestCase):
    def test_comprobante_no_es_publico_en_media(self):
        respuesta = self.client.get("/media/finanzas/comprobantes/2026/11/privado.pdf")
        self.assertEqual(respuesta.status_code, 404)

    def test_usuario_autenticado_no_puede_saltar_bloqueo_media(self):
        usuario = get_user_model().objects.create_user(username="usuario_finanzas_prueba", password="clave_segura_prueba")
        self.client.force_login(usuario)
        respuesta = self.client.get("/media/finanzas/pagos_facturas/2026/11/privado.pdf")
        self.assertEqual(respuesta.status_code, 404)

    def test_usuario_no_admin_no_descarga_comprobante_por_vista(self):
        usuario = get_user_model().objects.create_user(username="usuario_sin_permiso_finanzas", password="clave_segura_prueba")
        self.client.force_login(usuario)
        respuesta = self.client.get(reverse("finanzas_archivo", args=["ingreso", 999999]))
        self.assertEqual(respuesta.status_code, 403)
