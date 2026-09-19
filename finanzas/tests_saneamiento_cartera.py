from datetime import date
from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from clientes.models import Cliente
from contratos.models import Contrato
from finanzas.models import Factura, PagoFactura


class SaneamientoCarteraCommandTests(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create(nombre="Prueba saneamiento")
        self.contrato = Contrato.objects.create(
            cliente=self.cliente, precio_mensual=Decimal("40.00"), fecha_inicio=date(2026, 8, 4), activo=True
        )

    def factura(self, cuota, total_cuotas, total, mes=8):
        return Factura.objects.create(
            cliente=self.cliente, contrato=self.contrato, periodo_anio=2026, periodo_mes=mes,
            periodo_inicio=date(2026, mes, 4), periodo_fin=date(2026, 9 if mes == 8 else 10, 4),
            cuota_numero=cuota, total_cuotas=total_cuotas, fecha_vencimiento=date(2026, 9, 4),
            subtotal=total, total=total, valor_contractual=Decimal("40.00")
        )

    def test_dry_run_detecta_1_1_mas_2_2_y_no_modifica(self):
        self.factura(1, 1, Decimal("40.00"))
        sospechosa = self.factura(2, 2, Decimal("20.00"))
        out = StringIO()
        call_command("auditar_saneamiento_cartera", stdout=out)
        sospechosa.refresh_from_db()
        self.assertIn(sospechosa.id, [int(x) for x in out.getvalue().split("Candidatas sin pagos:")[1].split("->")[1].split("\n")[0].strip(" []").split(",") if x.strip()])
        self.assertNotEqual(sospechosa.estado, Factura.ESTADO_ANULADA)

    def test_apply_anula_solo_id_explicito_sin_pago(self):
        self.factura(1, 1, Decimal("40.00"))
        sospechosa = self.factura(2, 2, Decimal("20.00"))
        call_command("auditar_saneamiento_cartera", "--apply", "--invoice-ids", str(sospechosa.id), stdout=StringIO())
        sospechosa.refresh_from_db()
        self.assertEqual(sospechosa.estado, Factura.ESTADO_ANULADA)

    def test_apply_rechaza_factura_con_pago(self):
        self.factura(1, 1, Decimal("40.00"))
        sospechosa = self.factura(2, 2, Decimal("20.00"))
        PagoFactura.objects.create(factura=sospechosa, monto=Decimal("20.00"), fecha=date(2026, 9, 4))
        out = StringIO()
        call_command("auditar_saneamiento_cartera", stdout=out)
        self.assertIn(str(sospechosa.id), out.getvalue())
        self.assertIn("revision manual", out.getvalue().lower())
