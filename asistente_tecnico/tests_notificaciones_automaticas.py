"""Pruebas de aislamiento y recordatorios AQUO360 sin usar modelos internos del ERP."""
import json
from datetime import timedelta
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from .models import (PerfilSuscriptor, PiscinaSuscriptor, PlanMantenimientoPiscina,
                     VisitaProgramadaPiscina, NotificacionDigital, SuscripcionPushDigital)
from .notificaciones_automaticas import generar_recordatorios_mantenimientos


class NotificacionesDigitalesTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.a = User.objects.create_user('suscriptor_a17', password='Test12345!')
        self.b = User.objects.create_user('suscriptor_b17', password='Test12345!')
        self.pa = PerfilSuscriptor.objects.create(user=self.a, plan='profesional', estado='activo')
        self.pb = PerfilSuscriptor.objects.create(user=self.b, plan='empresarial', estado='activo')
        self.piscina = PiscinaSuscriptor.objects.create(suscriptor=self.pa, nombre='Piscina A', volumen_m3=40)
        self.otra = PiscinaSuscriptor.objects.create(suscriptor=self.pb, nombre='Piscina B', volumen_m3=30)
        hoy = timezone.localdate()
        self.plan = PlanMantenimientoPiscina.objects.create(piscina=self.piscina, dias_semana=[hoy.weekday()])
        self.plan_b = PlanMantenimientoPiscina.objects.create(piscina=self.otra, dias_semana=[hoy.weekday()])

    def test_recordatorio_idempotente_y_aislado(self):
        generar_recordatorios_mantenimientos()
        generar_recordatorios_mantenimientos()
        self.assertEqual(NotificacionDigital.objects.filter(suscriptor=self.pa, tipo='visita_hoy').count(), 1)
        self.assertEqual(NotificacionDigital.objects.filter(suscriptor=self.pb, tipo='visita_hoy').count(), 1)
        self.assertNotEqual(NotificacionDigital.objects.get(suscriptor=self.pa).piscina_id,
                            NotificacionDigital.objects.get(suscriptor=self.pb).piscina_id)

    def test_no_recordatorio_si_visita_realizada(self):
        VisitaProgramadaPiscina.objects.create(plan=self.plan, piscina=self.piscina,
                                               fecha=timezone.localdate(), estado='completada')
        generar_recordatorios_mantenimientos()
        self.assertFalse(NotificacionDigital.objects.filter(suscriptor=self.pa).exists())

    def test_endpoints_aislados_y_permiso(self):
        ruta = reverse('asistente_tecnico:digital_push_suscribir')
        payload = {'endpoint': 'https://ejemplo.com/' + 'x'*30,
                   'keys': {'p256dh': 'a'*40, 'auth': 'b'*30}}
        self.client.force_login(self.a)
        response = self.client.post(ruta, json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.client.force_login(self.b)
        response = self.client.post(ruta, json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 409)
        self.assertEqual(SuscripcionPushDigital.objects.get(endpoint=payload['endpoint']).suscriptor_id, self.pa.pk)

    def test_cliente_no_puede_borrar_endpoints_ajenos(self):
        sub = SuscripcionPushDigital.objects.create(suscriptor=self.pa,
            endpoint='https://ejemplo.com/'+'z'*30, p256dh='a'*40, auth='b'*30)
        self.client.force_login(self.b)
        ruta = reverse('asistente_tecnico:digital_push_cancelar')
        response = self.client.post(ruta, json.dumps({'endpoint': sub.endpoint}), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(SuscripcionPushDigital.objects.filter(pk=sub.pk).exists())
