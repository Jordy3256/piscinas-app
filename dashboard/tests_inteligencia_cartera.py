from datetime import date,timedelta
from decimal import Decimal
from django.test import TestCase
from clientes.models import Cliente
from contratos.models import Contrato
from finanzas.models import Factura
from dashboard.inteligencia_cartera import analizar_cartera_inteligente
class InteligenciaCarteraTests(TestCase):
    def test_prioriza_factura_vencida(self):
        hoy=date(2026,9,12); c=Cliente.objects.create(nombre="Cliente mora",telefono="0999999999",direccion="Prueba")
        co=Contrato.objects.create(cliente=c,frecuencia="1_semanal",forma_pago="adelantado",precio_mensual=Decimal("600"),valor_tecnico_mensual=Decimal("50"),fecha_inicio=date(2026,1,1),fecha_inicio_original=date(2026,1,1))
        Factura.objects.create(cliente=c,contrato=co,numero="TEST-CARTERA-1",periodo_anio=2026,periodo_mes=7,fecha_emision=date(2026,7,1),fecha_vencimiento=hoy-timedelta(days=65),total=Decimal("600"),valor_contractual=Decimal("600"),estado=Factura.ESTADO_VENCIDA)
        r=analizar_cartera_inteligente(hoy=hoy)
        self.assertEqual(r["vencido"],Decimal("600.00")); self.assertEqual(r["clientes_prioritarios"],1); self.assertEqual(r["ranking"][0]["prioridad"],"Cobrar hoy")
