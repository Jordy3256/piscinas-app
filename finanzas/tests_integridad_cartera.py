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

    def test_50_50_nunca_supera_precio_mensual(self):
        contrato = self._contrato(
            precio_mensual=Decimal("80.00"),
            forma_pago="50_50",
            programacion_cobro="dos_pagos",
            porcentaje_primer_pago=Decimal("50.00"),
        )
        cuotas = contrato.calendario_cobros(2026, 9)
        self.assertEqual(len(cuotas), 2)
        self.assertEqual(sum((c["valor"] for c in cuotas), Decimal("0.00")), Decimal("80.00"))

    def test_por_visita_nunca_supera_precio_mensual(self):
        from mantenimientos.models import Mantenimiento
        contrato = self._contrato(
            precio_mensual=Decimal("80.00"),
            forma_pago="por_visita",
            programacion_cobro="por_visita",
        )
        for fecha_visita in (date(2026, 9, 26), date(2026, 10, 3), date(2026, 10, 10)):
            Mantenimiento.objects.create(contrato=contrato, cliente=self.cliente, fecha=fecha_visita)
        cuotas = contrato.calendario_cobros(2026, 9)
        self.assertEqual(sum((c["valor"] for c in cuotas), Decimal("0.00")), Decimal("80.00"))
