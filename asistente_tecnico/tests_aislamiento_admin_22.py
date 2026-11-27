"""Pruebas para la independencia administrativa AQUO360."""
import unittest
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from .models import AvisoAdministrativoAquo, PerfilSuscriptor, SolicitudSuscripcionDigital
from .views import _notificar_admin_digital
from dashboard.models import Notificacion

class AislamientoAdministrativoAquoTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user("admin22", password="x", is_staff=True)
        self.otro = User.objects.create_user("cliente22", password="x")
        self.perfil = PerfilSuscriptor.objects.create(user=self.otro, plan="individual", estado="pendiente")

    def test_el_aviso_no_usa_tabla_del_erp(self):
        _notificar_admin_digital("Nuevo pago", "Pago a verificar")
        self.assertEqual(AvisoAdministrativoAquo.objects.filter(usuario=self.admin).count(), 1)
        self.assertEqual(Notificacion.objects.count(), 0)
