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

    def test_individual_bloquea_sexto_mensaje(self):
        for i in range(5):
            MensajeSoporteDigital.objects.create(
                conversacion=self.conv, remitente="cliente", autor=self.user, texto=f"m{i}"
            )
        response = self.client.post(
            reverse("asistente_tecnico:digital_soporte_chat", args=[self.conv.pk]),
            {"mensaje": "sexto"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json()["codigo"], "limite_soporte_diario")

    def test_burbuja_cliente_muestra_conversacion_activa(self):
        response = self.client.get(reverse("asistente_tecnico:digital_soporte_burbuja_api"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["visible"])
        self.assertEqual(response.json()["conversacion_id"], self.conv.pk)


class BurbujaSoporteAdminTests(TestCase):
    def test_admin_recibe_burbuja_con_mensaje_no_leido(self):
        User = get_user_model()
        admin = User.objects.create_user("admin-support", password="x", is_staff=True)
        user = User.objects.create_user("digital-user", password="x")
        perfil = PerfilSuscriptor.objects.create(
            user=user, estado="activo", plan="individual",
            acceso_hasta=timezone.localdate() + timedelta(days=30),
        )
        conv = ConversacionSoporteDigital.objects.create(suscriptor=perfil, estado="espera_admin")
        MensajeSoporteDigital.objects.create(
            conversacion=conv, remitente="cliente", autor=user, texto="Hola", leido_admin=False
        )
        self.client.force_login(admin)
        response = self.client.get(reverse("asistente_tecnico:soporte_admin_burbuja_api"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["visible"])
        self.assertEqual(response.json()["no_leidos"], 1)
