from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from clientes.models import Cliente
from contratos.models import Contrato
from finanzas.cuentas_por_cobrar import cuotas_programadas_para_mes_cobro
from finanzas.models import Factura
from finanzas.sincronizacion import sincronizar_contrato_activo


class IntegridadCarteraTests(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create(
            nombre="Administracion Costa Brisa",
            telefono="0990000000",
            ciudad="Manta",
            direccion="Costa Brisa",
        )

    def _contrato(self, **extra):
        datos = {
            "cliente": self.cliente,
            "tipo": "semanal",
            "frecuencia": "1_semanal",
            "forma_pago": "adelantado",
            "programacion_cobro": "inicio_periodo",
            "precio_mensual": Decimal("250.00"),
            "fecha_inicio": date(2026, 2, 25),
            "periodo_dia_inicio": 25,
            "generacion_automatica": False,
            "activo": False,
        }
        datos.update(extra)
        contrato = Contrato.objects.create(**datos)
        # Activamos sin ejecutar post_save para probar explícitamente la rutina
        # financiera con una fecha controlada.
        Contrato.objects.filter(pk=contrato.pk).update(activo=True)
        contrato.refresh_from_db()
        return contrato

    def test_ciclo_25_a_25_no_omite_el_periodo_vigente(self):
        contrato = self._contrato()

        resultado = sincronizar_contrato_activo(
            contrato,
            desde_fecha=date(2026, 9, 17),
            horizonte_meses=0,
        )

        factura = Factura.objects.get(
            contrato=contrato,
            periodo_anio=2026,
            periodo_mes=8,
            cuota_numero=1,
        )
        self.assertEqual(factura.periodo_inicio, date(2026, 8, 25))
        self.assertEqual(factura.periodo_fin, date(2026, 9, 25))
        self.assertEqual(factura.fecha_cobro_desde, date(2026, 8, 25))
        self.assertEqual(factura.fecha_vencimiento, date(2026, 8, 25))
        self.assertEqual(resultado["facturas_creadas"], 1)

    def test_mes_de_cobro_es_independiente_del_mes_de_servicio(self):
        contrato = self._contrato(
            forma_pago="fin_mensualidad",
            programacion_cobro="cierre_periodo",
        )
        cuotas_octubre = cuotas_programadas_para_mes_cobro(contrato, 2026, 10)
        claves = {(anio, mes, cuota["fecha_cobro_desde"]) for anio, mes, cuota in cuotas_octubre}
        self.assertIn((2026, 9, date(2026, 10, 25)), claves)

    def test_cuenta_programada_futura_no_es_cartera_exigible(self):
        contrato = self._contrato()
        hoy = timezone.localdate()
        futura = hoy + timedelta(days=45)
        factura = Factura.objects.create(
            cliente=self.cliente,
            contrato=contrato,
            periodo_anio=futura.year,
            periodo_mes=futura.month,
            periodo_inicio=futura,
            periodo_fin=futura + timedelta(days=30),
            fecha_cobro_desde=futura,
            fecha_vencimiento=futura,
            subtotal=Decimal("250.00"),
            impuesto=Decimal("0.00"),
            total=Decimal("250.00"),
            valor_contractual=Decimal("250.00"),
        )
        self.assertTrue(factura.es_programada_futura)
        self.assertEqual(factura.estado_gestion, "programada")
        self.assertEqual(factura.estado_gestion_label, "Programada")

class EsquemaHistoricoCarteraTests(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create(
            nombre="Cliente histórico 50/50",
            telefono="0991111111",
            ciudad="Guayaquil",
            direccion="Prueba",
        )
        self.contrato = Contrato.objects.create(
            cliente=self.cliente,
            tipo="semanal",
            frecuencia="1_semanal",
            forma_pago="adelantado",
            programacion_cobro="inicio_periodo",
            precio_mensual=Decimal("40.00"),
            fecha_inicio=date(2026, 3, 4),
            periodo_dia_inicio=4,
            generacion_automatica=False,
            activo=False,
        )
        Contrato.objects.filter(pk=self.contrato.pk).update(activo=True)
        self.contrato.refresh_from_db()

    def test_periodo_1_de_1_no_se_fragmenta_retroactivamente_a_50_50(self):
        from finanzas.cuentas_por_cobrar import generar_factura_contrato

        Factura.objects.create(
            cliente=self.cliente,
            contrato=self.contrato,
            periodo_anio=2026,
            periodo_mes=8,
            periodo_inicio=date(2026, 8, 4),
            periodo_fin=date(2026, 9, 4),
            cuota_numero=1,
            total_cuotas=1,
            fecha_emision=date(2026, 7, 30),
            fecha_cobro_desde=date(2026, 8, 4),
            fecha_vencimiento=date(2026, 8, 4),
            subtotal=Decimal("40.00"),
            impuesto=Decimal("0.00"),
            total=Decimal("40.00"),
            valor_contractual=Decimal("40.00"),
        )

        Contrato.objects.filter(pk=self.contrato.pk).update(
            forma_pago="50_50",
            programacion_cobro="dos_pagos",
            porcentaje_primer_pago=Decimal("50.00"),
        )
        self.contrato.refresh_from_db()

        creadas, cantidad = generar_factura_contrato(self.contrato, 2026, 8)

        self.assertEqual(cantidad, 0)
        self.assertEqual(creadas, [])
        self.assertEqual(
            list(Factura.objects.filter(contrato=self.contrato, periodo_anio=2026, periodo_mes=8)
                 .values_list("cuota_numero", "total_cuotas", "total")),
            [(1, 1, Decimal("40.00"))],
        )

    def test_periodo_nuevo_si_usa_50_50(self):
        from finanzas.cuentas_por_cobrar import generar_factura_contrato

        Contrato.objects.filter(pk=self.contrato.pk).update(
            forma_pago="50_50",
            programacion_cobro="dos_pagos",
            porcentaje_primer_pago=Decimal("50.00"),
        )
        self.contrato.refresh_from_db()

        _, cantidad = generar_factura_contrato(self.contrato, 2026, 9)
        facturas = list(
            Factura.objects.filter(contrato=self.contrato, periodo_anio=2026, periodo_mes=9)
            .order_by("cuota_numero")
        )

        self.assertEqual(cantidad, 2)
        self.assertEqual([(f.cuota_numero, f.total_cuotas, f.total) for f in facturas], [
            (1, 2, Decimal("20.00")),
            (2, 2, Decimal("20.00")),
        ])
