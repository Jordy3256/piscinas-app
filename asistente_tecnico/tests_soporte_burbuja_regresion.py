from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from asistente_tecnico.models import (
    PerfilSuscriptor,
    ConversacionSoporteDigital,
    MensajeSoporteDigital,
)


class SoporteBurbujaRegresionTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.cliente = User.objects.create_user(
            "bubble-reg-client",
            password="x",
        )
        self.admin = User.objects.create_user(
            "bubble-reg-admin",
            password="x",
            is_staff=True,
        )
        self.perfil = PerfilSuscriptor.objects.create(
            user=self.cliente,
            estado="activo",
            plan="individual",
            acceso_hasta=timezone.localdate() + timedelta(days=30),
        )
        self.conv = ConversacionSoporteDigital.objects.create(
            suscriptor=self.perfil,
            asunto="Soporte",
            estado="espera_admin",
        )

    def test_api_admin_no_da_500_y_detecta_mensaje_cliente(self):
        msg = MensajeSoporteDigital.objects.create(
            conversacion=self.conv,
            remitente="cliente",
            autor=self.cliente,
            texto="Necesito ayuda",
            leido_admin=False,
            leido_cliente=True,
        )
        self.client.force_login(self.admin)
        response = self.client.get(
            reverse("asistente_tecnico:soporte_admin_burbuja_api")
        )
        self.assertEqual(response.status_code, 200)
        item = next(
            x for x in response.json()["conversaciones"]
            if x["id"] == self.conv.pk
        )
        self.assertEqual(item["no_leidos"], 1)
        self.assertEqual(item["ultimo_entrante_id"], msg.pk)

    def test_api_cliente_no_da_500_y_detecta_respuesta_admin(self):
        msg = MensajeSoporteDigital.objects.create(
            conversacion=self.conv,
            remitente="admin",
            autor=self.admin,
            texto="Ya te respondimos",
            leido_cliente=False,
            leido_admin=True,
        )
        self.client.force_login(self.cliente)
        response = self.client.get(
            reverse("asistente_tecnico:digital_soporte_burbuja_api")
        )
        self.assertEqual(response.status_code, 200)
        item = next(
            x for x in response.json()["conversaciones"]
            if x["id"] == self.conv.pk
        )
        self.assertEqual(item["no_leidos"], 1)
        self.assertEqual(item["ultimo_entrante_id"], msg.pk)
