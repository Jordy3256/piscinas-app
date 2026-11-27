"""El comprobante digital local no debe servirse públicamente."""
import unittest
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
