"""Pruebas de aislamiento AQUO360: ejecutar python manage.py test asistente_tecnico.tests_digital_registros."""
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from .models import PerfilSuscriptor, PiscinaSuscriptor, PlanMantenimientoPiscina, VisitaProgramadaPiscina, RegistroMantenimientoPiscina
from django.utils import timezone


class RegistroEmpresarialAislamientoTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.empresa = User.objects.create_user(username="aquo_empresa_test", password="testS3guro!")
        self.ajeno = User.objects.create_user(username="aquo_otro_test", password="testS3guro!")
        self.tecnico = User.objects.create_user(username="aquo_tecnico_test", password="testS3guro!")
        self.p_empresa = PerfilSuscriptor.objects.create(user=self.empresa, estado="activo", plan="empresarial")
        self.p_otro = PerfilSuscriptor.objects.create(user=self.ajeno, estado="activo", plan="empresarial")
        self.p_tecnico = PerfilSuscriptor.objects.create(user=self.tecnico, estado="activo", plan="profesional")
        self.piscina = PiscinaSuscriptor.objects.create(suscriptor=self.p_empresa, nombre="Piscina privada 1", volumen_m3=Decimal("50"))
        self.plan = PlanMantenimientoPiscina.objects.create(piscina=self.piscina)
        self.visita = VisitaProgramadaPiscina.objects.create(plan=self.plan, piscina=self.piscina, fecha=timezone.localdate())
        self.url = reverse("asistente_tecnico:digital_visita_detallada", args=[self.visita.pk])

    def test_empresa_puede_cerrar_una_visita_una_sola_vez(self):
        self.client.force_login(self.empresa)
        datos = {"ph": "7.4", "cloro": "2.0", "tareas": ["aspirado", "filtros"], "cloro_granulado": "120"}
        self.assertEqual(self.client.post(self.url, datos).status_code, 302)
        self.assertEqual(self.client.post(self.url, datos).status_code, 302)
        self.assertEqual(RegistroMantenimientoPiscina.objects.filter(visita=self.visita).count(), 1)
        self.visita.refresh_from_db()
        self.assertEqual(self.visita.estado, "completada")
        self.assertEqual(RegistroMantenimientoPiscina.objects.get(visita=self.visita).quimicos["cloro_granulado"], "120")

    def test_otro_suscriptor_no_puede_leer_ni_modificar(self):
        self.client.force_login(self.ajeno)
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertEqual(self.client.post(self.url, {"tareas": ["aspirado"]}).status_code, 404)
        self.assertEqual(RegistroMantenimientoPiscina.objects.count(), 0)

    def test_profesional_no_puede_registrar_detalles(self):
        self.client.force_login(self.tecnico)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertEqual(self.client.post(self.url, {}).status_code, 403)

    def test_empresa_no_puede_burlar_cierre_desde_agenda(self):
        self.client.force_login(self.empresa)
        response = self.client.post(reverse("asistente_tecnico:digital_agenda"), {"visita_id": self.visita.pk})
        self.assertEqual(response.status_code, 302)
        self.visita.refresh_from_db()
        self.assertEqual(self.visita.estado, "programada")
