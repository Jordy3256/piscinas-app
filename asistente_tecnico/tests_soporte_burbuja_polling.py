from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from asistente_tecnico.models import PerfilSuscriptor, ConversacionSoporteDigital, MensajeSoporteDigital

class SoporteBurbujaPollingTests(TestCase):
    def setUp(self):
        User=get_user_model()
        self.cliente=User.objects.create_user("poll-client",password="x")
        self.admin=User.objects.create_user("poll-admin",password="x",is_staff=True)
        self.perfil=PerfilSuscriptor.objects.create(
            user=self.cliente,estado="activo",plan="individual",
            acceso_hasta=timezone.localdate()+timedelta(days=30)
        )
        self.conv=ConversacionSoporteDigital.objects.create(suscriptor=self.perfil,asunto="Soporte")

    def test_poll_admin_detecta_mensaje_creado_despues(self):
        self.client.force_login(self.admin)
        antes=self.client.get(reverse("asistente_tecnico:soporte_admin_burbuja_api")).json()
        item0=[x for x in antes["conversaciones"] if x["id"]==self.conv.pk][0]
        self.assertEqual(item0["no_leidos"],0)
        msg=MensajeSoporteDigital.objects.create(
            conversacion=self.conv,remitente="cliente",autor=self.cliente,
            texto="nuevo",leido_admin=False,leido_cliente=True
        )
        despues=self.client.get(reverse("asistente_tecnico:soporte_admin_burbuja_api")).json()
        item=[x for x in despues["conversaciones"] if x["id"]==self.conv.pk][0]
        self.assertEqual(item["no_leidos"],1)
        self.assertEqual(item["ultimo_entrante_id"],msg.pk)

    def test_poll_cliente_detecta_respuesta_creada_despues(self):
        self.client.force_login(self.cliente)
        antes=self.client.get(reverse("asistente_tecnico:digital_soporte_burbuja_api")).json()
        item0=[x for x in antes["conversaciones"] if x["id"]==self.conv.pk][0]
        self.assertEqual(item0["no_leidos"],0)
        msg=MensajeSoporteDigital.objects.create(
            conversacion=self.conv,remitente="admin",autor=self.admin,
            texto="respuesta",leido_cliente=False,leido_admin=True
        )
        despues=self.client.get(reverse("asistente_tecnico:digital_soporte_burbuja_api")).json()
        item=[x for x in despues["conversaciones"] if x["id"]==self.conv.pk][0]
        self.assertEqual(item["no_leidos"],1)
        self.assertEqual(item["ultimo_entrante_id"],msg.pk)
