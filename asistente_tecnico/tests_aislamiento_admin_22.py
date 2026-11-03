"""Pruebas para la independencia administrativa AQUO360."""
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

    def test_cliente_no_puede_ver_bandeja_ni_comprobante(self):
        solicitud = SolicitudSuscripcionDigital.objects.create(suscriptor=self.perfil, tipo="alta", plan="individual", valor="1.99")
        self.client.force_login(self.otro)
        self.assertEqual(self.client.get(reverse("asistente_tecnico:digital_avisos_admin")).status_code, 403)
        self.assertEqual(self.client.get(reverse("asistente_tecnico:digital_comprobante_admin", args=[solicitud.pk])).status_code, 403)

    def test_avisos_solo_del_administrador_actual(self):
        otro_admin = get_user_model().objects.create_user("admin22dos", password="x", is_staff=True)
        AvisoAdministrativoAquo.objects.create(usuario=otro_admin, titulo="Privado", mensaje="No visible")
        self.client.force_login(self.admin)
        response = self.client.get(reverse("asistente_tecnico:digital_avisos_admin"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "No visible")
