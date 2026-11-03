"""Pruebas de regresión pre-lanzamiento de AQUO360.

Nunca usa los modelos ni tablas de contratos, mantenimientos o finanzas de JVAQUA.
Ejecutar: python manage.py test asistente_tecnico.tests_pre_lanzamiento
"""
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import (
    CobroPiscinaDigital, NotificacionDigital, PagoCobroDigital,
    PerfilSuscriptor, PiscinaSuscriptor, SolicitudSuscripcionDigital,
)


class AislamientoYLanzamientoTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.usuarios = {}
        self.perfiles = {}
        for plan in ('individual', 'esencial', 'profesional', 'empresarial'):
            usuario = User.objects.create_user(username=f'aquo_{plan}_qa', password='ClaveSeguraPrueba778!')
            perfil = PerfilSuscriptor.objects.create(
                user=usuario, plan=plan, estado='activo',
                acceso_hasta=timezone.localdate() + timedelta(days=20),
            )
            self.usuarios[plan] = usuario
            self.perfiles[plan] = perfil
        self.piscina_empresarial = PiscinaSuscriptor.objects.create(
            suscriptor=self.perfiles['empresarial'], nombre='Cliente empresarial privado',
            volumen_m3=Decimal('40.00'), valor_mensual=Decimal('95.00'), dia_cobro=15,
        )
        self.cobro = CobroPiscinaDigital.objects.create(
            piscina=self.piscina_empresarial,
            periodo=timezone.localdate().replace(day=1),
            vencimiento=timezone.localdate() + timedelta(days=5),
            importe=Decimal('95.00'),
        )

    def test_limites_y_permisos_de_los_cuatro_planes(self):
        limites = {'individual': 1, 'esencial': 3, 'profesional': 30, 'empresarial': None}
        soporte = {'individual': 5, 'esencial': 10, 'profesional': 50, 'empresarial': 100}
        for plan, perfil in self.perfiles.items():
            with self.subTest(plan=plan):
                self.assertEqual(perfil.limite_piscinas, limites[plan])
                self.assertEqual(perfil.limite_mensajes_soporte_diario, soporte[plan])
                self.assertEqual(perfil.puede_agenda, plan in ('profesional', 'empresarial'))
                self.assertEqual(perfil.puede_registrar_mantenimientos, plan == 'empresarial')
                self.assertEqual(perfil.puede_recordatorios_cobro, plan == 'empresarial')

    def test_solo_empresarial_puede_acceder_a_cartera(self):
        url = reverse('asistente_tecnico:digital_cartera')
        for plan, usuario in self.usuarios.items():
            self.client.force_login(usuario)
            respuesta = self.client.get(url)
            self.assertEqual(respuesta.status_code, 200 if plan == 'empresarial' else 403)

    def test_cliente_ajeno_no_consulta_ficha_de_piscina(self):
        url = reverse('asistente_tecnico:digital_piscina_detalle', args=[self.piscina_empresarial.pk])
        for plan in ('individual', 'esencial', 'profesional'):
            self.client.force_login(self.usuarios[plan])
            self.assertEqual(self.client.get(url).status_code, 404)

    def test_cliente_ajeno_no_registra_pago_de_otra_empresa(self):
        otra_empresa = get_user_model().objects.create_user(username='aquo_otra_empresa_qa', password='ClaveSeguraPrueba778!')
        PerfilSuscriptor.objects.create(
            user=otra_empresa, plan='empresarial', estado='activo',
            acceso_hasta=timezone.localdate() + timedelta(days=20),
        )
        self.client.force_login(otra_empresa)
        url = reverse('asistente_tecnico:digital_cobro_pago', args=[self.cobro.pk])
        respuesta = self.client.post(url, {'importe': '50.00', 'fecha_pago': timezone.localdate().isoformat()})
        self.assertEqual(respuesta.status_code, 404)
        self.assertFalse(PagoCobroDigital.objects.filter(cobro=self.cobro).exists())

    def test_planes_personales_no_pueden_registrar_pagos(self):
        url = reverse('asistente_tecnico:digital_cobro_pago', args=[self.cobro.pk])
        for plan in ('individual', 'esencial', 'profesional'):
            self.client.force_login(self.usuarios[plan])
            self.assertEqual(self.client.post(url, {
                'importe': '10', 'fecha_pago': timezone.localdate().isoformat(),
            }).status_code, 403)
        self.assertFalse(PagoCobroDigital.objects.exists())

    def test_notificacion_ajena_no_se_puede_marcar_leida(self):
        aviso = NotificacionDigital.objects.create(
            suscriptor=self.perfiles['empresarial'], tipo='recordatorio',
            titulo='Aviso privado', mensaje='Solo empresa',
            programada_para=timezone.now() - timedelta(minutes=5),
        )
        self.client.force_login(self.usuarios['individual'])
        url = reverse('asistente_tecnico:digital_notificacion_leer', args=[aviso.pk])
        self.assertEqual(self.client.post(url).status_code, 404)
        aviso.refresh_from_db()
        self.assertFalse(aviso.leida)

    def test_notificacion_no_redirige_a_web_externa(self):
        aviso = NotificacionDigital.objects.create(
            suscriptor=self.perfiles['empresarial'], tipo='recordatorio',
            titulo='Prueba redirección', mensaje='Mensaje',
            programada_para=timezone.now() - timedelta(minutes=5),
        )
        self.client.force_login(self.usuarios['empresarial'])
        url = reverse('asistente_tecnico:digital_notificacion_leer', args=[aviso.pk])
        for destino in ('//sitio-externo.example/robar', '/dashboard/home/', 'https://sitio-externo.example'):
            respuesta = self.client.post(url, {'next': destino})
            self.assertEqual(respuesta.status_code, 302)
            self.assertEqual(respuesta['Location'], reverse('asistente_tecnico:digital_notificaciones'))

    def test_notificacion_permite_destino_digital_local(self):
        aviso = NotificacionDigital.objects.create(
            suscriptor=self.perfiles['empresarial'], tipo='recordatorio',
            titulo='Prueba local', mensaje='Mensaje',
            programada_para=timezone.now() - timedelta(minutes=5),
        )
        self.client.force_login(self.usuarios['empresarial'])
        destino = reverse('asistente_tecnico:digital_inicio')
        respuesta = self.client.post(
            reverse('asistente_tecnico:digital_notificacion_leer', args=[aviso.pk]),
            {'next': destino},
        )
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(respuesta['Location'], destino)

    @patch('asistente_tecnico.views._notificar_admin_digital')
    def test_pago_no_cambia_plan_antes_de_aprobacion(self, _notificar):
        self.client.force_login(self.usuarios['individual'])
        self.client.post(reverse('asistente_tecnico:digital_acceso'), {
            'plan': 'empresarial', 'metodo_envio': 'whatsapp',
        })
        self.perfiles['individual'].refresh_from_db()
        self.assertEqual(self.perfiles['individual'].plan, 'individual')
        self.assertFalse(self.perfiles['individual'].puede_recordatorios_cobro)
        solicitud = SolicitudSuscripcionDigital.objects.get(suscriptor=self.perfiles['individual'])
        self.assertEqual(solicitud.plan, 'empresarial')
        self.assertEqual(solicitud.estado, 'pendiente')

    def test_cuenta_vencida_no_entra_a_cartera(self):
        perfil = self.perfiles['empresarial']
        perfil.acceso_hasta = timezone.localdate() - timedelta(days=1)
        perfil.save(update_fields=['acceso_hasta'])
        self.client.force_login(self.usuarios['empresarial'])
        self.assertEqual(self.client.get(reverse('asistente_tecnico:digital_cartera')).status_code, 403)
