from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from clientes.models import Cliente
from contratos.models import Contrato
from trabajadores.models import Trabajador
from contratos.programacion import generar_mantenimientos_contrato


class VigenciaContratoTests(TestCase):
    def _contrato(self, **kwargs):
        cliente = Cliente.objects.create(nombre="Cliente Vigencia", telefono="0999999999")
        user = User.objects.create_user(username="tec_vigencia")
        trabajador = Trabajador.objects.create(user=user, telefono="0999999999")
        datos = dict(
            cliente=cliente,
            tipo="semanal",
            frecuencia="1_semanal",
            forma_pago="adelantado",
            programacion_cobro="inicio_periodo",
            precio_mensual=Decimal("55.00"),
            fecha_inicio=date(2026, 9, 12),
            tecnico_designado=trabajador,
            dias_visita=[5],
            generacion_automatica=True,
            activo=True,
        )
        datos.update(kwargs)
        return Contrato.objects.create(**datos)

    def test_vigencia_12_meses_calcula_ultimo_dia(self):
        contrato = self._contrato(vigencia_meses=12)
        self.assertEqual(contrato.fecha_fin_contrato, date(2027, 9, 11))

    def test_semestral_adelantado_asume_vigencia_anual(self):
        contrato = self._contrato(
            forma_pago="semestral_adelantado",
            programacion_cobro="semestral_adelantado",
            vigencia_meses=None,
        )
        self.assertEqual(contrato.vigencia_meses, 12)
        self.assertEqual(contrato.fecha_fin_contrato, date(2027, 9, 11))

    def test_programacion_no_supera_fecha_fin(self):
        contrato = self._contrato(vigencia_meses=1)
        resultado = generar_mantenimientos_contrato(
            contrato,
            desde=date(2026, 9, 12),
            hasta=date(2026, 11, 30),
        )
        self.assertLessEqual(resultado["hasta"], contrato.fecha_fin_contrato)
        self.assertFalse(contrato.mantenimientos.filter(fecha__gt=contrato.fecha_fin_contrato).exists())
