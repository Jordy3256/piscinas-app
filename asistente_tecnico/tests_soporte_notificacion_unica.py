from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from dashboard.models import Notificacion
from asistente_tecnico.models import PerfilSuscriptor, ConversacionSoporteDigital, MensajeSoporteDigital
from asistente_tecnico.views import _sincronizar_notificacion_admin_soporte


class SoporteNotificacionUnicaTests(TestCase):
    def test_una_sola_notificacion_para_multiples_mensajes(self):
        User = get_user_model()
        admin = User.objects.create_user("admin-soporte-unico", password="x", is_staff=True)
        cliente = User.objects.create_user("cliente-soporte-unico", password="x")
        perfil = PerfilSuscriptor.objects.create(
            user=cliente,
            estado="activo",
            plan="individual",
            acceso_hasta=timezone.localdate() + timedelta(days=30),
        )
        conv = ConversacionSoporteDigital.objects.create(suscriptor=perfil, asunto="Ayuda")

        for i in range(3):
            MensajeSoporteDigital.objects.create(
                conversacion=conv,
                remitente="cliente",
                autor=cliente,
                texto=f"Mensaje {i}",
                leido_admin=False,
            )
            _sincronizar_notificacion_admin_soporte()

        qs = Notificacion.objects.filter(
            user=admin,
            tipo="general",
            referencia_id=-9001,
        )
        self.assertEqual(qs.count(), 1)
        self.assertIn("3 mensaje", qs.first().mensaje)

        conv.mensajes.filter(remitente="cliente").update(leido_admin=True)
        _sincronizar_notificacion_admin_soporte()
        self.assertFalse(qs.exists())
