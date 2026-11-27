"""Pruebas del flujo de pago AQUO360 (sin datos del ERP interno)."""
import unittest
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from .models import PerfilSuscriptor, SolicitudSuscripcionDigital


class FlujoSuscripcionAquoTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.cliente = User.objects.create_user(
            username="suscriptor_lanzamiento@example.com", password="ClaveDePrueba987!"
        )
        self.admin = User.objects.create_superuser(
            username="admin_lanzamiento@example.com", email="admin_lanzamiento@example.com",
            password="ClaveDePrueba987!"
        )
        self.perfil = PerfilSuscriptor.objects.create(
            user=self.cliente, plan="individual", estado="activo",
            acceso_hasta=timezone.localdate() + timedelta(days=10),
        )
        self.url_pago = reverse("asistente_tecnico:digital_acceso")





    @patch("asistente_tecnico.views._notificar_admin_digital")
    def test_alta_nueva_queda_inactiva_hasta_aprobacion(self, _notificar):
        self.perfil.estado = "pendiente"
        self.perfil.acceso_hasta = None
        self.perfil.save()
        self.client.force_login(self.cliente)
        self.client.post(self.url_pago, {"plan": "profesional", "metodo_envio": "whatsapp"})
        self.perfil.refresh_from_db()
        self.assertFalse(self.perfil.tiene_acceso)
        self.assertEqual(self.perfil.plan, "individual")
