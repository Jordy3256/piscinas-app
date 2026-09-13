from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from asistente_tecnico.models import PerfilSuscriptor, ConversacionSoporteDigital, MensajeSoporteDigital, NotificacionDigital

class SoporteMultichatNotificacionesTests(TestCase):
    def setUp(self):
        User=get_user_model()
        self.user=User.objects.create_user("multi",password="x")
        self.perfil=PerfilSuscriptor.objects.create(user=self.user,estado="activo",plan="profesional",acceso_hasta=timezone.localdate()+timedelta(days=30))
        self.client.force_login(self.user)

    def test_api_cliente_devuelve_multiples(self):
        c1=ConversacionSoporteDigital.objects.create(suscriptor=self.perfil,asunto="Uno")
        c2=ConversacionSoporteDigital.objects.create(suscriptor=self.perfil,asunto="Dos")
        MensajeSoporteDigital.objects.create(conversacion=c1,remitente="admin",texto="Hola",leido_cliente=False)
        r=self.client.get(reverse("asistente_tecnico:digital_soporte_burbuja_api"))
        self.assertEqual(r.status_code,200)
        ids={x["id"] for x in r.json()["conversaciones"]}
        self.assertIn(c1.pk,ids);self.assertIn(c2.pk,ids);self.assertEqual(r.json()["no_leidos"],1)

    def test_eliminar_notificacion(self):
        n=NotificacionDigital.objects.create(suscriptor=self.perfil,tipo="recordatorio",titulo="X",mensaje="Y",programada_para=timezone.now())
        r=self.client.post(reverse("asistente_tecnico:digital_notificacion_eliminar",args=[n.pk]))
        self.assertEqual(r.status_code,302);self.assertFalse(NotificacionDigital.objects.filter(pk=n.pk).exists())

    def test_eliminar_todas(self):
        for i in range(2):
            NotificacionDigital.objects.create(suscriptor=self.perfil,tipo="recordatorio",titulo=str(i),mensaje="Y",programada_para=timezone.now())
        r=self.client.post(reverse("asistente_tecnico:digital_notificaciones_eliminar_todas"))
        self.assertEqual(r.status_code,302);self.assertEqual(self.perfil.notificaciones_digitales.count(),0)
