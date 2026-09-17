from datetime import date
from decimal import Decimal

from django.test import TestCase

from clientes.models import Cliente
from contratos.models import Contrato
from mantenimientos.models import Mantenimiento

from finanzas.cuentas_por_cobrar import generar_factura_contrato
from finanzas.facturacion_externa import sincronizar_avisos_facturacion
from finanzas.models import AvisoFacturacion, Factura
from finanzas.sincronizacion import sincronizar_contrato_activo


class PagoPorVisitaTests(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create(
            nombre="Cliente visita",
            telefono="0999999999",
            ciudad="Guayaquil",
            direccion="Dirección de prueba",
        )
        self.contrato = Contrato.objects.create(
            cliente=self.cliente,
            tipo="semanal",
            frecuencia="1_semanal",
            forma_pago="por_visita",
            programacion_cobro="inicio_periodo",  # save debe corregirlo
            precio_mensual=Decimal("100.00"),
            aplica_iva=True,
            fecha_inicio=date(2026, 9, 1),
            periodo_dia_inicio=1,
            generacion_automatica=False,
            activo=True,
            requiere_factura=True,
            momento_facturacion="antes_cobro",  # save debe corregirlo
        )
        for dia in (4, 11, 18, 25):
            Mantenimiento.objects.create(
                cliente=self.cliente,
                contrato=self.contrato,
                fecha=date(2026, 9, dia),
                estado="pendiente",
                automatico=False,
            )

    def test_contrato_fuerza_cobro_y_facturacion_por_visita(self):
        self.contrato.refresh_from_db()
        self.assertEqual(self.contrato.programacion_cobro, "por_visita")
        self.assertEqual(self.contrato.momento_facturacion, "por_visita")

    def test_calendario_reparte_valor_mensual_entre_visitas_con_iva(self):
        cuotas = self.contrato.calendario_cobros(2026, 9)
        self.assertEqual(len(cuotas), 4)
        self.assertEqual([c["fecha_vencimiento"] for c in cuotas], [
            date(2026, 9, 4), date(2026, 9, 11),
            date(2026, 9, 18), date(2026, 9, 25),
        ])
        self.assertEqual(sum((c["valor"] for c in cuotas), Decimal("0.00")), Decimal("100.00"))
        self.assertEqual(sum((c["impuesto"] for c in cuotas), Decimal("0.00")), Decimal("15.00"))
        self.assertEqual(sum((c["total"] for c in cuotas), Decimal("0.00")), Decimal("115.00"))

    def test_cartera_crea_una_cuenta_por_visita(self):
        creadas, cantidad = generar_factura_contrato(self.contrato, 2026, 9)
        self.assertEqual(cantidad, 4)
        facturas = list(
            Factura.objects.filter(contrato=self.contrato)
            .exclude(estado=Factura.ESTADO_ANULADA)
            .order_by("cuota_numero")
        )
        self.assertEqual(len(facturas), 4)
        self.assertEqual(sum((f.subtotal for f in facturas), Decimal("0.00")), Decimal("100.00"))
        self.assertEqual(sum((f.impuesto for f in facturas), Decimal("0.00")), Decimal("15.00"))
        self.assertEqual(sum((f.total for f in facturas), Decimal("0.00")), Decimal("115.00"))
        self.assertEqual(facturas[0].fecha_vencimiento, date(2026, 9, 4))
        self.assertEqual(facturas[0].fecha_facturacion_programada, date(2026, 9, 4))

    def test_facturacion_externa_crea_un_aviso_por_visita(self):
        resultado = sincronizar_avisos_facturacion(
            hoy=date(2026, 9, 1),
            meses_atras=0,
            meses_adelante=0,
        )
        self.assertEqual(resultado["errores"], [])
        avisos = list(
            AvisoFacturacion.objects.filter(
                contrato=self.contrato,
                periodo_anio=2026,
                periodo_mes=9,
                estado=AvisoFacturacion.ESTADO_PENDIENTE,
            ).order_by("cuota_numero")
        )
        self.assertEqual(len(avisos), 4)
        self.assertEqual(
            [a.fecha_programada for a in avisos],
            [date(2026, 9, 4), date(2026, 9, 11), date(2026, 9, 18), date(2026, 9, 25)],
        )

    def test_cancelar_una_visita_retira_documentos_pendientes_sobrantes(self):
        generar_factura_contrato(self.contrato, 2026, 9)
        sincronizar_avisos_facturacion(
            hoy=date(2026, 9, 1),
            meses_atras=0,
            meses_adelante=0,
        )

        Mantenimiento.objects.filter(
            contrato=self.contrato,
            fecha=date(2026, 9, 25),
        ).delete()

        sincronizar_contrato_activo(
            self.contrato,
            desde_fecha=date(2026, 9, 1),
            horizonte_meses=0,
        )
        sincronizar_avisos_facturacion(
            hoy=date(2026, 9, 1),
            meses_atras=0,
            meses_adelante=0,
        )

        activas = Factura.objects.filter(
            contrato=self.contrato,
        ).exclude(estado=Factura.ESTADO_ANULADA)
        avisos = AvisoFacturacion.objects.filter(
            contrato=self.contrato,
            estado=AvisoFacturacion.ESTADO_PENDIENTE,
        )
        self.assertEqual(activas.count(), 3)
        self.assertEqual(avisos.count(), 3)
