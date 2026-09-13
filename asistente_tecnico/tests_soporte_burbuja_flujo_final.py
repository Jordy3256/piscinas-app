from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from asistente_tecnico.models import PerfilSuscriptor, ConversacionSoporteDigital, MensajeSoporteDigital

class SoporteBurbujaFlujoFinalTests(TestCase):
    def setUp(self):
        User=get_user_model()
        self.cliente=User.objects.create_user("bubble-final-client",password="x")
        self.admin=User.objects.create_user("bubble-final-admin",password="x",is_staff=True)
        self.perfil=PerfilSuscriptor.objects.create(
            user=self.cliente,estado="activo",plan="individual",
            acceso_hasta=timezone.localdate()+timedelta(days=30)
        )

    def test_admin_detecta_nuevo_mensaje_cliente(self):
        conv=ConversacionSoporteDigital.objects.create(suscriptor=self.perfil,asunto="Ayuda")
        msg=MensajeSoporteDigital.objects.create(
            conversacion=conv,remitente="cliente",autor=self.cliente,
            texto="Hola",leido_admin=False,leido_cliente=True
        )
        self.client.force_login(self.admin)
        data=self.client.get(reverse("asistente_tecnico:soporte_admin_burbuja_api")).json()
        item=data["conversaciones"][0]
        self.assertEqual(item["no_leidos"],1)
        self.assertEqual(item["ultimo_entrante_id"],msg.pk)

    def test_cliente_detecta_respuesta_admin(self):
        conv=ConversacionSoporteDigital.objects.create(suscriptor=self.perfil,asunto="Ayuda")
        msg=MensajeSoporteDigital.objects.create(
            conversacion=conv,remitente="admin",autor=self.admin,
            texto="Respuesta",leido_cliente=False,leido_admin=True
        )
        self.client.force_login(self.cliente)
        data=self.client.get(reverse("asistente_tecnico:digital_soporte_burbuja_api")).json()
        item=data["conversaciones"][0]
        self.assertEqual(item["no_leidos"],1)
        self.assertEqual(item["ultimo_entrante_id"],msg.pk)
