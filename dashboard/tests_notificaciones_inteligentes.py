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

    @patch('dashboard.notificaciones_inteligentes._admin_users', return_value=[])
    @patch('dashboard.notificaciones_inteligentes.Trabajador.objects.filter')
    @patch('dashboard.notificaciones_inteligentes.Mantenimiento.objects.filter')
    @patch('dashboard.notificaciones_inteligentes._notify_once', return_value=True)
    def test_resumen_20h_llega_al_trabajador_con_pendientes(self, notify, mantenimientos_filter, trabajadores_filter, admins):
        from types import SimpleNamespace
        trabajador = SimpleNamespace(pk=42, user=self.user, activo=True)
        visita = SimpleNamespace(fecha=date(2026, 10, 27), trabajadores=SimpleNamespace(all=lambda: [trabajador]))
        mantenimientos_filter.return_value.prefetch_related.return_value.iterator.return_value = iter([visita])
        trabajadores_filter.return_value.select_related.return_value = [trabajador]
        resultado = enviar_resumenes(20, fecha=date(2026, 10, 27))
        self.assertEqual(resultado['trabajadores'], 1)
        self.assertEqual(resultado['pendientes'], 1)
        self.assertEqual(notify.call_args.args[1], 'resumen_trabajador')
        self.assertIn('20:00', notify.call_args.args[4])

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

class OrdenTrabajoPushTests(TestCase):
    def setUp(self):
        from trabajadores.models import Trabajador
        self.user = get_user_model().objects.create_user('orden_push_prueba', password='test-only')
        self.trabajador = Trabajador.objects.create(user=self.user, telefono='0999999999')

    @patch('dashboard.views._send_push_to_user')
    def test_orden_genera_notificacion_interna_y_push(self, push):
        from types import SimpleNamespace
        from ordenes_trabajo.views import _notificar_trabajador
        orden = SimpleNamespace(pk=123, trabajador=self.trabajador)
        with self.captureOnCommitCallbacks(execute=True):
            _notificar_trabajador(orden, 'Orden asignada', 'Nueva orden')
        notif = Notificacion.objects.get(user=self.user)
        self.assertEqual(notif.url, '/dashboard/ordenes/123/')
        self.assertEqual(notif.referencia_id, 123)
        push.assert_called_once()
        self.assertEqual(push.call_args.kwargs['url'], notif.url)

    @patch('dashboard.views._send_push_to_user', return_value={'ok': False, 'error': 'Usuario sin suscripciones push'})
    def test_orden_registra_diagnostico_si_no_hay_entrega(self, push):
        from types import SimpleNamespace
        from ordenes_trabajo.views import _notificar_trabajador
        orden = SimpleNamespace(pk=124, trabajador=self.trabajador)
        with self.assertLogs('ordenes_trabajo.views', level='WARNING') as registros:
            with self.captureOnCommitCallbacks(execute=True):
                _notificar_trabajador(orden, 'Orden asignada', 'Nueva orden')
        self.assertTrue(any('ORDEN_PUSH sin_entrega' in linea for linea in registros.output))
        self.assertEqual(Notificacion.objects.filter(user=self.user, referencia_id=124).count(), 1)
        push.assert_called_once()
