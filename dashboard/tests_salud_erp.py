from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from clientes.models import Cliente
from contratos.models import Contrato
from dashboard.salud_erp import diagnosticar_salud_erp
from trabajadores.models import Trabajador


class SaludERPTests(TestCase):
    def setUp(self):
        self.hoy = date(2026, 9, 12)
        self.cliente = Cliente.objects.create(
            nombre="Cliente Salud",
            telefono="0999999999",
            direccion="Dirección Test",
        )

    def test_detecta_contrato_automatico_sin_tecnico(self):
        Contrato.objects.create(
            cliente=self.cliente,
            tipo="semanal",
            frecuencia="1_semanal",
            forma_pago="adelantado",
            programacion_cobro="inicio_periodo",
            precio_mensual=Decimal("60.00"),
            fecha_inicio=self.hoy,
            dias_visita=[5],
            generacion_automatica=True,
            activo=True,
        )
        diagnostico = diagnosticar_salud_erp(hoy=self.hoy)
        claves = {item["clave"] for item in diagnostico["items"]}
        self.assertIn("contratos_sin_tecnico", claves)

    def test_detecta_contrato_vencido(self):
        user = User.objects.create_user(username="tec_salud")
        trabajador = Trabajador.objects.create(user=user, telefono="0999999998")
        contrato = Contrato.objects.create(
            cliente=self.cliente,
            tipo="semanal",
            frecuencia="1_semanal",
            forma_pago="adelantado",
            programacion_cobro="inicio_periodo",
            precio_mensual=Decimal("60.00"),
            fecha_inicio=date(2026, 7, 1),
            vigencia_meses=1,
            tecnico_designado=trabajador,
            dias_visita=[2],
            generacion_automatica=True,
            activo=True,
        )
        self.assertLess(contrato.fecha_fin_contrato, self.hoy)
        diagnostico = diagnosticar_salud_erp(hoy=self.hoy)
        claves = {item["clave"] for item in diagnostico["items"]}
        self.assertIn("contratos_vencidos", claves)
