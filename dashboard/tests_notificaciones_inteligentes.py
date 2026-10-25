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


class SuscripcionesCaducadasTests(TestCase):
    def setUp(self):
        from dashboard.models import PushSubscription
        self.user = get_user_model().objects.create_user('push_caducado_prueba', password='test-only')
        self.expirada = PushSubscription.objects.create(
            user=self.user, endpoint='https://push.example.invalid/expired',
            p256dh='test-p256dh', auth='test-auth',
        )
        self.vigente = PushSubscription.objects.create(
            user=self.user, endpoint='https://push.example.invalid/valid',
            p256dh='test-p256dh', auth='test-auth',
        )

    @patch('dashboard.views.webpush')
    @patch('dashboard.views._push_status_code_from_exception', return_value=410)
    @patch('dashboard.views.settings')
    def test_410_elimina_solo_suscripcion_caducada(self, settings, status, webpush_mock):
        from dashboard.models import PushSubscription
        from dashboard.views import _send_push_to_user, WebPushException
        settings.VAPID_PRIVATE_KEY = 'test-key'
        settings.VAPID_SUBJECT = 'mailto:test@example.com'
        webpush_mock.side_effect = lambda **kwargs: (_ for _ in ()).throw(WebPushException('gone')) if kwargs['subscription_info']['endpoint'].endswith('/expired') else None
        result = _send_push_to_user(self.user, 'Prueba', 'Texto')
        self.assertEqual(result['sent'], 1)
        self.assertEqual(result['failed'], 1)
        self.assertFalse(PushSubscription.objects.filter(pk=self.expirada.pk).exists())
        self.assertTrue(PushSubscription.objects.filter(pk=self.vigente.pk).exists())

    @patch('dashboard.views.webpush')
    @patch('dashboard.views._push_status_code_from_exception', return_value=500)
    @patch('dashboard.views.settings')
    def test_error_temporal_no_elimina_suscripciones(self, settings, status, webpush_mock):
        from dashboard.models import PushSubscription
        from dashboard.views import _send_push_to_user, WebPushException
        settings.VAPID_PRIVATE_KEY = 'test-key'
        settings.VAPID_SUBJECT = 'mailto:test@example.com'
        webpush_mock.side_effect = WebPushException('temporary')
        _send_push_to_user(self.user, 'Prueba', 'Texto')
        self.assertEqual(PushSubscription.objects.filter(user=self.user).count(), 2)
