from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from asistente_tecnico.models import PerfilSuscriptor, ConversacionSoporteDigital, MensajeSoporteDigital


class LimitesSoporteDigitalTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user("digital-limit", password="x")
        self.perfil = PerfilSuscriptor.objects.create(
            user=self.user,
            estado="activo",
            plan="individual",
            acceso_hasta=timezone.localdate() + timedelta(days=30),
        )
        self.conv = ConversacionSoporteDigital.objects.create(
            suscriptor=self.perfil,
            asunto="Prueba",
            estado="espera_admin",
        )
        self.client.force_login(self.user)

    def test_limites_por_plan(self):
        self.assertEqual(self.perfil.limite_mensajes_soporte_diario, 5)
        self.perfil.plan = "esencial"
        self.assertEqual(self.perfil.limite_mensajes_soporte_diario, 10)
        self.perfil.plan = "profesional"
        self.assertEqual(self.perfil.limite_mensajes_soporte_diario, 50)
