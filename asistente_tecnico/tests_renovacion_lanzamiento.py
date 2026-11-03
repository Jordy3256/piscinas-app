"""Pruebas de renovación y aislamiento de suscriptores AQUO360."""
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from asistente_tecnico.models import PerfilSuscriptor, NotificacionDigital
from asistente_tecnico.notificaciones_automaticas import generar_avisos_renovacion, _aviso_vigente


class RecordatoriosRenovacionTests(TestCase):
    def setUp(self):
        hoy = timezone.localdate()
        User = get_user_model()
        self.a = PerfilSuscriptor.objects.create(
            user=User.objects.create_user(username="cliente_a_renovacion", password="test-pwd-123"),
            estado="activo", plan="individual", acceso_hasta=hoy + timedelta(days=3))
        self.b = PerfilSuscriptor.objects.create(
            user=User.objects.create_user(username="cliente_b_renovacion", password="test-pwd-123"),
            estado="activo", plan="empresarial", acceso_hasta=hoy + timedelta(days=10))

    def test_generar_un_aviso_sin_duplicarlo(self):
        self.assertEqual(generar_avisos_renovacion(), 1)
        self.assertEqual(generar_avisos_renovacion(), 0)
        aviso = NotificacionDigital.objects.get(tipo="suscripcion_proxima")
        self.assertEqual(aviso.suscriptor_id, self.a.pk)
        self.assertTrue(_aviso_vigente(aviso))

    def test_no_mezclar_avisos_entre_suscriptores(self):
        generar_avisos_renovacion()
        self.assertFalse(NotificacionDigital.objects.filter(suscriptor=self.b).exists())

    def test_renovacion_aprobada_invalida_aviso_anterior(self):
        generar_avisos_renovacion()
        aviso = NotificacionDigital.objects.get(suscriptor=self.a)
        self.a.acceso_hasta += timedelta(days=30)
        self.a.save(update_fields=["acceso_hasta"])
        aviso.suscriptor.refresh_from_db()
        self.assertFalse(_aviso_vigente(aviso))

    def test_suscripcion_vencida_no_crea_nuevos_avisos(self):
        self.a.acceso_hasta = timezone.localdate() - timedelta(days=1)
        self.a.save(update_fields=["acceso_hasta"])
        self.assertEqual(generar_avisos_renovacion(), 0)
