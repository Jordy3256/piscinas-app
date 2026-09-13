from datetime import date
from decimal import Decimal

from django.test import TestCase

from clientes.models import Cliente
from contratos.models import Contrato
from dashboard.inteligencia_crecimiento import analizar_crecimiento_retencion


class InteligenciaCrecimientoTests(TestCase):
    def test_baja_reduce_retencion_y_facturacion(self):
        cliente = Cliente.objects.create(nombre="Cliente crecimiento", telefono="0999999999")
        Contrato.objects.create(
            cliente=cliente, frecuencia="1_semanal", forma_pago="adelantado",
            precio_mensual=Decimal("100.00"), valor_tecnico_mensual=Decimal("20.00"),
            fecha_inicio=date(2026, 8, 1), fecha_inicio_original=date(2026, 8, 1),
            fecha_baja=date(2026, 9, 10), motivo_baja="precio", activo=False,
        )
        analisis = analizar_crecimiento_retencion(hoy=date(2026, 9, 12))
        self.assertEqual(analisis["actual"]["bajas"], 1)
        self.assertEqual(analisis["actual"]["ingreso_perdido"], Decimal("100.00"))
        self.assertLess(analisis["actual"]["retencion"], 100)
