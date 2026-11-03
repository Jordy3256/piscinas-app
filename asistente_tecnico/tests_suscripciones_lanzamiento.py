"""Pruebas del flujo de pago AQUO360 (sin datos del ERP interno)."""
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from .models import PerfilSuscriptor, SolicitudSuscripcionDigital


class FlujoSuscripcionAquoTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.cliente = User.objects.create_user(
            username="suscriptor_lanzamiento@example.com", password="ClaveDePrueba987!"
        )
        self.admin = User.objects.create_superuser(
            username="admin_lanzamiento@example.com", email="admin_lanzamiento@example.com",
            password="ClaveDePrueba987!"
        )
        self.perfil = PerfilSuscriptor.objects.create(
            user=self.cliente, plan="individual", estado="activo",
            acceso_hasta=timezone.localdate() + timedelta(days=10),
        )
        self.url_pago = reverse("asistente_tecnico:digital_acceso")

    @patch("asistente_tecnico.views._notificar_admin_digital")
    def test_solicitar_upgrade_no_habilita_empresarial(self, _notificar):
        self.client.force_login(self.cliente)
        r = self.client.post(self.url_pago, {
            "plan": "empresarial", "metodo_envio": "whatsapp",
        })
        self.assertEqual(r.status_code, 200)
        self.perfil.refresh_from_db()
        self.assertEqual(self.perfil.plan, "individual")
        self.assertTrue(self.perfil.tiene_acceso)
        self.assertFalse(self.perfil.puede_recordatorios_cobro)
        solicitud = SolicitudSuscripcionDigital.objects.get(suscriptor=self.perfil)
        self.assertEqual(solicitud.plan, "empresarial")
        self.assertEqual(solicitud.valor, Decimal("19.99"))

    @patch("asistente_tecnico.views._notificar_admin_digital")
    def test_repetir_envio_no_crea_dos_solicitudes(self, _notificar):
        self.client.force_login(self.cliente)
        self.client.post(self.url_pago, {"plan": "profesional", "metodo_envio": "whatsapp"})
        self.client.force_login(self.cliente)
        self.client.post(self.url_pago, {"plan": "empresarial", "metodo_envio": "whatsapp"})
        self.assertEqual(SolicitudSuscripcionDigital.objects.filter(suscriptor=self.perfil).count(), 1)

    @patch("asistente_tecnico.views._notificar_admin_digital")
    def test_aprobar_activa_plan_solicitado_y_extiende_periodo(self, _notificar):
        self.client.force_login(self.cliente)
        self.client.post(self.url_pago, {"plan": "empresarial", "metodo_envio": "whatsapp"})
        solicitud = SolicitudSuscripcionDigital.objects.get(suscriptor=self.perfil)
        fecha_anterior = self.perfil.acceso_hasta
        self.client.force_login(self.admin)
        r = self.client.post(reverse("asistente_tecnico:digital_suscripcion_revisar", args=[solicitud.pk]),
                             {"accion": "aprobar"})
        self.assertEqual(r.status_code, 302)
        self.perfil.refresh_from_db()
        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, "aprobada")
        self.assertEqual(self.perfil.plan, "empresarial")
        self.assertEqual(self.perfil.acceso_hasta, fecha_anterior + timedelta(days=30))

    @patch("asistente_tecnico.views._notificar_admin_digital")
    def test_rechazar_conserva_plan_actual(self, _notificar):
        self.client.force_login(self.cliente)
        self.client.post(self.url_pago, {"plan": "empresarial", "metodo_envio": "whatsapp"})
        solicitud = SolicitudSuscripcionDigital.objects.get(suscriptor=self.perfil)
        self.client.force_login(self.admin)
        self.client.post(reverse("asistente_tecnico:digital_suscripcion_revisar", args=[solicitud.pk]),
                         {"accion": "rechazar"})
        self.perfil.refresh_from_db()
        self.assertEqual(self.perfil.plan, "individual")
        self.assertTrue(self.perfil.tiene_acceso)

    @patch("asistente_tecnico.views._notificar_admin_digital")
    def test_alta_nueva_queda_inactiva_hasta_aprobacion(self, _notificar):
        self.perfil.estado = "pendiente"
        self.perfil.acceso_hasta = None
        self.perfil.save()
        self.client.force_login(self.cliente)
        self.client.post(self.url_pago, {"plan": "profesional", "metodo_envio": "whatsapp"})
        self.perfil.refresh_from_db()
        self.assertFalse(self.perfil.tiene_acceso)
        self.assertEqual(self.perfil.plan, "individual")

    @patch("asistente_tecnico.views._notificar_admin_digital")
    def test_renovacion_pendiente_no_cierra_sesion_activa(self, _notificar):
        self.client.force_login(self.cliente)
        respuesta = self.client.post(self.url_pago, {
            "plan": "empresarial", "metodo_envio": "whatsapp",
        })
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.context["mantiene_acceso"])
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.cliente.pk)
        self.assertEqual(
            self.client.get(reverse("asistente_tecnico:digital_inicio")).status_code, 200
        )
        self.perfil.refresh_from_db()
        self.assertEqual(self.perfil.plan, "individual")
        self.assertEqual(
            SolicitudSuscripcionDigital.objects.get(suscriptor=self.perfil).estado,
            "pendiente",
        )

    @patch("asistente_tecnico.views._notificar_admin_digital")
    def test_alta_pendiente_si_cierra_sesion(self, _notificar):
        self.perfil.estado = "pendiente"
        self.perfil.acceso_hasta = None
        self.perfil.save(update_fields=["estado", "acceso_hasta"])
        self.client.force_login(self.cliente)
        respuesta = self.client.post(self.url_pago, {
            "plan": "individual", "metodo_envio": "whatsapp",
        })
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(respuesta.context["mantiene_acceso"])
        self.assertNotIn("_auth_user_id", self.client.session)
        self.perfil.refresh_from_db()
        self.assertFalse(self.perfil.tiene_acceso)
