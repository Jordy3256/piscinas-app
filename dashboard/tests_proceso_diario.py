from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase

from clientes.models import Cliente
from contratos.models import Contrato
from dashboard.models import Notificacion
from dashboard.proceso_diario import ejecutar_proceso_diario_jvaqua
from trabajadores.models import Trabajador


class ProcesoDiarioJVAQUATests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="admin_diario", is_staff=True)
        self.cliente = Cliente.objects.create(nombre="Cliente Diario", telefono="0999999999")
        self.user_tec = User.objects.create_user(username="tec_diario")
        self.trabajador = Trabajador.objects.create(user=self.user_tec, telefono="0999999998")

    def _contrato(self, **kwargs):
        datos = dict(
            cliente=self.cliente,
            tipo="semanal",
            frecuencia="1_semanal",
            forma_pago="adelantado",
            programacion_cobro="inicio_periodo",
            precio_mensual=Decimal("55.00"),
            valor_tecnico_mensual=Decimal("20.00"),
            fecha_inicio=date(2026, 9, 12),
            tecnico_designado=self.trabajador,
            dias_visita=[5],
            generacion_automatica=True,
            activo=True,
        )
        datos.update(kwargs)
        return Contrato.objects.create(**datos)

    def test_contrato_vencido_genera_alerta_administrativa(self):
        contrato = self._contrato(vigencia_meses=1)
        hoy = date(2026, 10, 20)
        with patch("dashboard.proceso_diario.generar_alertas_financieras", return_value=0), \
             patch("dashboard.proceso_diario.materializar_consumos_contratos", return_value=0), \
             patch("dashboard.proceso_diario.sincronizar_avisos_facturacion", return_value={"creados":0,"actualizados":0,"anulados":0,"errores":[]}):
            ejecutar_proceso_diario_jvaqua(hoy=hoy, enviar_push=False)
        self.assertTrue(
            Notificacion.objects.filter(
                user=self.admin,
                tipo="contrato_vencido",
                referencia_id=contrato.pk,
            ).exists()
        )

    def test_calendario_no_cobra_despues_de_vencimiento(self):
        contrato = self._contrato(vigencia_meses=1)
        self.assertEqual(contrato.fecha_fin_contrato, date(2026, 10, 11))
        self.assertEqual(contrato.calendario_cobros(2026, 10), [])
