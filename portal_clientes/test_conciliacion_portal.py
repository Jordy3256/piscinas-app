"""Pruebas sin base de datos de la selección y conciliación visual."""
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from django.test import SimpleTestCase
from .conciliacion import resumir_facturas


class FacturaFalsa(SimpleNamespace):
    ESTADO_ANULADA = 'anulada'
    ESTADO_PAGADA = 'pagada'
    ESTADO_PROMOCION = 'promocion'


def fila(pk, contrato, cobro, vencimiento, saldo, pagado='0', estado='pendiente', pagos=None):
    f = FacturaFalsa(pk=pk, contrato_id=contrato, fecha_real_cobro=cobro,
                     fecha_vencimiento=vencimiento, pagada_en=None, estado=estado)
    return {'factura': f, 'saldo': Decimal(saldo), 'pagado': Decimal(pagado),
            'pagos': pagos or []}


class ConciliacionPortalTests(SimpleTestCase):
    HOY = date(2026, 11, 21)

    def test_varias_vencidas_muestra_una_pero_suma_todas(self):
        filas = [fila(1, 1, date(2026, 9, 10), date(2026, 9, 10), '40'),
                 fila(2, 1, date(2026, 10, 10), date(2026, 10, 10), '30'),
                 fila(3, 1, date(2026, 12, 10), date(2026, 12, 10), '50')]
        proximas, _, saldo, vencido, _ = resumir_facturas(filas, self.HOY)
        self.assertEqual(len(proximas), 1)
        self.assertEqual(proximas[0]['factura'].pk, 1)
        self.assertEqual(saldo, Decimal('40'))
        self.assertEqual(vencido, Decimal('70'))

    def test_abono_y_promocion(self):
        filas = [fila(1, 1, date(2026, 10, 10), date(2026, 10, 10), '25', '20', pagos=[object()]),
                 fila(2, 1, date(2026, 11, 10), date(2026, 11, 10), '0', estado='promocion'),
                 fila(3, 2, date(2026, 12, 10), date(2026, 12, 10), '50')]
        proximas, historial, _, vencido, pagado = resumir_facturas(filas, self.HOY)
        self.assertEqual(len(proximas), 2)
        self.assertEqual(len(historial), 2)
        self.assertEqual(vencido, Decimal('25'))
        self.assertEqual(pagado, Decimal('20'))

    def test_fecha_cobro_futura_no_se_considera_vencida(self):
        filas = [fila(1, 1, date(2026, 12, 1), date(2026, 11, 1), '45')]
        self.assertEqual(resumir_facturas(filas, self.HOY)[3], Decimal('0'))

    def test_anulada_no_aparece(self):
        filas = [fila(1, 1, date(2026, 10, 1), date(2026, 10, 1), '50', estado='anulada')]
        proximas, historial, saldo, vencido, pagado = resumir_facturas(filas, self.HOY)
        self.assertEqual((proximas, historial, saldo, vencido, pagado),
                         ([], [], Decimal('0'), Decimal('0'), Decimal('0')))
