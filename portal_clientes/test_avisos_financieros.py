"""Reglas puras para los avisos diarios de cartera."""
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from django.test import SimpleTestCase
from .notificaciones import _evento_cobro


class AvisosFinancierosTests(SimpleTestCase):
    HOY = date(2026, 11, 22)

    def factura(self, **cambios):
        datos = dict(pk=7, numero='FAC-7', fecha_real_cobro=date(2026, 11, 19),
                     saldo=Decimal('35.00'), estado='parcial', anulada_manual=False)
        datos.update(cambios)
        return SimpleNamespace(**datos)

    def test_dia_de_cobro(self):
        aviso = _evento_cobro(self.factura(fecha_real_cobro=self.HOY), self.HOY)
        self.assertEqual(aviso[0], 'cobro')

    def test_vencido_cada_tres_dias(self):
        for dias in (3, 6, 9):
            from datetime import timedelta
            aviso = _evento_cobro(self.factura(fecha_real_cobro=self.HOY-timedelta(days=dias)), self.HOY)
            self.assertEqual(aviso[0], 'vencido')
        for dias in (1, 2, 4, 5, 7):
            from datetime import timedelta
            self.assertIsNone(_evento_cobro(self.factura(fecha_real_cobro=self.HOY-timedelta(days=dias)), self.HOY))

    def test_abono_mantiene_saldo_restante(self):
        self.assertIn('$12.50', _evento_cobro(self.factura(saldo=Decimal('12.50')), self.HOY)[3])

    def test_pagada_promocion_anulada_sin_avisos(self):
        for cambios in (dict(saldo=Decimal('0')), dict(estado='promocion'),
                        dict(estado='anulada'), dict(anulada_manual=True)):
            self.assertIsNone(_evento_cobro(self.factura(**cambios), self.HOY))

    def test_factura_futura_sin_aviso(self):
        self.assertIsNone(_evento_cobro(self.factura(fecha_real_cobro=date(2026, 12, 1)), self.HOY))
