from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from asistente_tecnico.models import PerfilSuscriptor, ConversacionSoporteDigital, MensajeSoporteDigital

class SoporteBurbujasRenderTests(TestCase):
    def test_api_cliente_y_admin_exponen_conversacion(self):
        User=get_user_model()
        admin=User.objects.create_user("admin-bubble",password="x",is_staff=True)
        cliente=User.objects.create_user("client-bubble",password="x")
        perfil=PerfilSuscriptor.objects.create(user=cliente,estado="activo",plan="individual",acceso_hasta=timezone.localdate()+timedelta(days=30))
        conv=ConversacionSoporteDigital.objects.create(suscriptor=perfil,asunto="Ayuda")
        MensajeSoporteDigital.objects.create(conversacion=conv,remitente="cliente",autor=cliente,texto="Hola",leido_admin=False)

        self.client.force_login(cliente)
        r=self.client.get(reverse("asistente_tecnico:digital_soporte_burbuja_api"))
        self.assertEqual(r.status_code,200)
        self.assertEqual(r.json()["conversaciones"][0]["id"],conv.pk)

        self.client.force_login(admin)
        r=self.client.get(reverse("asistente_tecnico:soporte_admin_burbuja_api"))
        self.assertEqual(r.status_code,200)
        self.assertEqual(r.json()["conversaciones"][0]["id"],conv.pk)
        self.assertEqual(r.json()["conversaciones"][0]["no_leidos"],1)
