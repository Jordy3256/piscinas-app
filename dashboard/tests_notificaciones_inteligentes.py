from datetime import date
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase
from dashboard.models import Notificacion
from dashboard.notificaciones_inteligentes import _notify_once, enviar_resumenes


class NotificacionesInteligentesTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('operador_prueba', password='test-only')

    @patch('dashboard.views._send_push_to_user')
    def test_idempotencia(self, push):
        self.assertTrue(_notify_once(self.user, 'resumen_trabajador', 2026102408, 'Pendientes', 'Texto', '/dashboard/'))
        self.assertFalse(_notify_once(self.user, 'resumen_trabajador', 2026102408, 'Pendientes', 'Texto', '/dashboard/'))
        self.assertEqual(Notificacion.objects.filter(user=self.user).count(), 1)
        self.assertEqual(push.call_count, 1)

    def test_dry_run_no_guarda(self):
        self.assertTrue(_notify_once(self.user, 'resumen_trabajador', 2026102408, 'Pendientes', 'Texto', '/dashboard/', dry_run=True))
        self.assertFalse(Notificacion.objects.exists())

    def test_dia_sin_mantenimientos_no_notifica(self):
        result = enviar_resumenes(8, dry_run=False, fecha=date(2026, 10, 24))
        self.assertEqual(result['trabajadores'], 0)
        self.assertFalse(Notificacion.objects.exists())
