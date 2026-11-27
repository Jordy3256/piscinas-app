"""Validaciones de almacenamiento y permisos de comprobantes AQUO360."""
import unittest
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import PerfilSuscriptor, SolicitudSuscripcionDigital
from .private_storage import private_aquo_storage


class ComprobantesPrivadosAquoTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user("admin_private24", password="prueba", is_staff=True)
        self.cliente = User.objects.create_user("cliente_private24", password="prueba")
        self.perfil = PerfilSuscriptor.objects.create(user=self.cliente, plan="individual", estado="pendiente")

    def test_archivo_usa_storage_privado(self):
        campo = SolicitudSuscripcionDigital._meta.get_field("comprobante")
        self.assertIs(campo.storage, private_aquo_storage)
        self.assertEqual(campo.upload_to, "comprobantes/%Y/%m/")


    def test_comprobante_sin_url_publica(self):
        with self.assertRaises(ValueError):
            private_aquo_storage.url("comprobantes/2026/11/falso.pdf")
