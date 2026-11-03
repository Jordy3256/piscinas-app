"""El comprobante digital local no debe servirse públicamente."""
import tempfile
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import PerfilSuscriptor, SolicitudSuscripcionDigital


class ComprobantesPrivadosTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user("admin_media23", password="test", is_staff=True)
        self.cliente = User.objects.create_user("cliente_media23", password="test")
        self.perfil = PerfilSuscriptor.objects.create(user=self.cliente, plan="individual", estado="pendiente")

    def test_url_media_local_rechazada_sin_autenticacion(self):
        respuesta = self.client.get("/media/jvaqua_digital/comprobantes/2026/11/archivo.pdf")
        self.assertEqual(respuesta.status_code, 404)

    def test_url_media_local_rechazada_incluso_admin(self):
        self.client.force_login(self.admin)
        respuesta = self.client.get("/media/jvaqua_digital/comprobantes/2026/11/archivo.pdf")
        self.assertEqual(respuesta.status_code, 404)

    def test_comprobante_solo_por_vista_admin(self):
        with tempfile.TemporaryDirectory() as carpeta:
            with override_settings(MEDIA_ROOT=carpeta):
                ruta = Path(carpeta) / "jvaqua_digital/comprobantes/2026/11/archivo.pdf"
                ruta.parent.mkdir(parents=True, exist_ok=True)
                ruta.write_bytes(b"%PDF-1.4\narchivo de prueba")
                solicitud = SolicitudSuscripcionDigital.objects.create(
                    suscriptor=self.perfil, tipo="alta", plan="individual", valor="1.99",
                    comprobante="jvaqua_digital/comprobantes/2026/11/archivo.pdf",
                )
                enlace = reverse("asistente_tecnico:digital_comprobante_admin", args=[solicitud.pk])
                self.client.force_login(self.cliente)
                self.assertEqual(self.client.get(enlace).status_code, 403)
                self.client.force_login(self.admin)
                respuesta = self.client.get(enlace)
                self.assertEqual(respuesta.status_code, 200)
                self.assertEqual(b"".join(respuesta.streaming_content), ruta.read_bytes())
