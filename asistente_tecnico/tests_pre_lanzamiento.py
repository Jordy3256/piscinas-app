"""Pruebas de regresión pre-lanzamiento de AQUO360.

Nunca usa los modelos ni tablas de contratos, mantenimientos o finanzas de JVAQUA.
Ejecutar: python manage.py test asistente_tecnico.tests_pre_lanzamiento
"""
import unittest
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
