from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase

from clientes.models import Cliente
from contratos.models import Contrato
from inventario.models import Insumo, MovimientoInventario
from dashboard.inteligencia_inventario import analizar_inventario_inteligente


class InteligenciaInventarioTests(TestCase):
    def test_detecta_stock_critico_y_consumo_anormal(self):
        hoy = date(2026, 9, 12)
        cliente = Cliente.objects.create(nombre="Cliente consumo", telefono="0999999999", direccion="Prueba")
        contrato = Contrato.objects.create(
            cliente=cliente, frecuencia="1_semanal", forma_pago="adelantado",
            precio_mensual=Decimal("100.00"), valor_tecnico_mensual=Decimal("20.00"),
            fecha_inicio=date(2026, 1, 1), fecha_inicio_original=date(2026, 1, 1),
        )
        insumo = Insumo.objects.create(
            nombre="Cloro test", stock=Decimal("2.000"), stock_minimo=Decimal("5.000"),
            costo=Decimal("10.0000"),
        )
        viejo = MovimientoInventario.objects.create(
            insumo=insumo, tipo="consumo_contrato", cantidad=Decimal("1.000"),
            contrato=contrato, costo_unitario=Decimal("10.0000"), total_costo=Decimal("10.00"),
        )
        MovimientoInventario.objects.filter(pk=viejo.pk).update(fecha=date(2026, 8, 10))
        actual = MovimientoInventario.objects.create(
            insumo=insumo, tipo="consumo_contrato", cantidad=Decimal("2.000"),
            contrato=contrato, costo_unitario=Decimal("10.0000"), total_costo=Decimal("20.00"),
        )
        MovimientoInventario.objects.filter(pk=actual.pk).update(fecha=hoy)

        r = analizar_inventario_inteligente(hoy=hoy)
        self.assertGreaterEqual(r["criticos"], 1)
        self.assertEqual(r["anomalos"], 1)
        self.assertEqual(r["contratos"][0]["anomalo"], True)
        self.assertEqual(r["costo_mes"], Decimal("20.00"))
