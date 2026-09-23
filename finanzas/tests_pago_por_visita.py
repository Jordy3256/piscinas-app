from datetime import date
from decimal import Decimal

from django.test import TestCase

from clientes.models import Cliente
from contratos.models import Contrato
from mantenimientos.models import Mantenimiento
from trabajadores.models import Trabajador
from django.contrib.auth.models import User

from finanzas.cuentas_por_cobrar import generar_factura_contrato, generar_factura_visita_realizada
from finanzas.facturacion_externa import sincronizar_avisos_facturacion
from finanzas.models import AvisoFacturacion, Factura, ObligacionTrabajador
from finanzas.sincronizacion import sincronizar_nomina_por_visita


class PagoPorVisitaTests(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create(nombre="Cliente visita", telefono="0999999999", ciudad="Guayaquil", direccion="Prueba")
        user = User.objects.create_user(username="tecnico-visita")
        self.trabajador = Trabajador.objects.create(user=user, telefono="0999999999", tipo_remuneracion="por_contrato")
        self.contrato = Contrato.objects.create(
            cliente=self.cliente, tipo="semanal", frecuencia="1_semanal", forma_pago="por_visita",
            programacion_cobro="inicio_periodo", precio_mensual=Decimal("100.00"), aplica_iva=True,
            valor_tecnico_mensual=Decimal("40.00"), tecnico_designado=self.trabajador,
            fecha_inicio=date(2026, 9, 1), periodo_dia_inicio=1, generacion_automatica=False,
            activo=True, requiere_factura=True, momento_facturacion="antes_cobro",
        )
        self.visitas = []
        for dia in (4, 11, 18, 25):
            self.visitas.append(Mantenimiento.objects.create(
                cliente=self.cliente, contrato=self.contrato, fecha=date(2026, 9, dia), estado="pendiente", automatico=False,
            ))

    def test_programar_visitas_no_genera_cartera(self):
        creadas, cantidad = generar_factura_contrato(self.contrato, 2026, 9)
        self.assertEqual(cantidad, 0)
        self.assertFalse(Factura.objects.filter(contrato=self.contrato).exists())

    def test_una_visita_realizada_genera_solo_un_cobro(self):
        visita = self.visitas[0]
        visita.estado = "realizado"; visita.save(update_fields=["estado"])
        factura, creada = generar_factura_visita_realizada(visita)
        self.assertTrue(creada)
        self.assertEqual(Factura.objects.filter(contrato=self.contrato).exclude(estado=Factura.ESTADO_ANULADA).count(), 1)
        self.assertEqual(factura.subtotal, Decimal("25.00"))
        self.assertEqual(factura.total, Decimal("28.75"))
        # Repetir el evento no duplica el cobro.
        generar_factura_visita_realizada(visita)
        self.assertEqual(Factura.objects.filter(contrato=self.contrato).count(), 1)

    def test_nomina_devenga_solo_visitas_realizadas(self):
        visita = self.visitas[0]
        visita.estado = "realizado"; visita.save(update_fields=["estado"])
        obligacion = sincronizar_nomina_por_visita(visita)
        self.assertEqual(obligacion.valor_acordado, Decimal("10.00"))
        segunda = self.visitas[1]
        segunda.estado = "realizado"; segunda.save(update_fields=["estado"])
        obligacion = sincronizar_nomina_por_visita(segunda)
        self.assertEqual(obligacion.valor_acordado, Decimal("20.00"))
        self.assertEqual(ObligacionTrabajador.objects.filter(contrato=self.contrato).count(), 1)

    def test_aviso_facturacion_solo_nace_para_visita_realizada(self):
        sincronizar_avisos_facturacion(hoy=date(2026, 9, 1), meses_atras=0, meses_adelante=0)
        self.assertFalse(AvisoFacturacion.objects.filter(contrato=self.contrato, estado=AvisoFacturacion.ESTADO_PENDIENTE).exists())
        visita = self.visitas[0]
        visita.estado = "realizado"; visita.save(update_fields=["estado"])
        sincronizar_avisos_facturacion(hoy=date(2026, 9, 4), meses_atras=0, meses_adelante=0)
        self.assertEqual(AvisoFacturacion.objects.filter(contrato=self.contrato, estado=AvisoFacturacion.ESTADO_PENDIENTE).count(), 1)
