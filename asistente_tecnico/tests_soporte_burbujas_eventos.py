from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from asistente_tecnico.models import PerfilSuscriptor, ConversacionSoporteDigital, MensajeSoporteDigital

class SoporteBurbujasEventosTests(TestCase):
    def setUp(self):
        User=get_user_model()
        self.cliente=User.objects.create_user("cliente-eventos",password="x")
        self.admin=User.objects.create_user("admin-eventos",password="x",is_staff=True)
        self.perfil=PerfilSuscriptor.objects.create(user=self.cliente,estado="activo",plan="individual",acceso_hasta=timezone.localdate()+timedelta(days=30))

    def test_contador_cliente(self):
        conv=ConversacionSoporteDigital.objects.create(suscriptor=self.perfil,asunto="Consulta",estado="espera_cliente")
        MensajeSoporteDigital.objects.create(conversacion=conv,remitente="admin",autor=self.admin,texto="Respuesta",leido_cliente=False,leido_admin=True)
        self.client.force_login(self.cliente)
        r=self.client.get(reverse("asistente_tecnico:digital_soporte_burbuja_api"))
        self.assertEqual(r.status_code,200)
        self.assertEqual(r.json()["conversaciones"][0]["no_leidos"],1)

    def test_contador_admin(self):
        conv=ConversacionSoporteDigital.objects.create(suscriptor=self.perfil,asunto="Consulta",estado="espera_admin")
        MensajeSoporteDigital.objects.create(conversacion=conv,remitente="cliente",autor=self.cliente,texto="Ayuda",leido_admin=False,leido_cliente=True)
        self.client.force_login(self.admin)
        r=self.client.get(reverse("asistente_tecnico:soporte_admin_burbuja_api"))
        self.assertEqual(r.status_code,200)
        self.assertEqual(r.json()["conversaciones"][0]["no_leidos"],1)
