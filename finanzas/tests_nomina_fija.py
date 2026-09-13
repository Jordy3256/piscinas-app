from decimal import Decimal
from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase

from clientes.models import Ciudad, Cliente
from contratos.models import Contrato
from trabajadores.models import Trabajador
from finanzas.models import ObligacionTrabajador
from finanzas.sincronizacion import materializar_nomina_fija_trabajador


class NominaFijaTests(TestCase):
    def setUp(self):
        self.ciudad = Ciudad.objects.create(nombre="Ciudad Test", activa=True)
        self.user = User.objects.create_user(username="tecnico_fijo")
        self.trabajador = Trabajador.objects.create(
            user=self.user,
            telefono="000",
            ciudad_principal=self.ciudad,
            activo=True,
            tipo_remuneracion="mensual_fija",
            sueldo_mensual_fijo=Decimal("600.00"),
            fecha_ingreso=date(2026, 9, 1),
        )

    def test_una_sola_obligacion_por_mes(self):
        materializar_nomina_fija_trabajador(
            self.trabajador,
            desde_fecha=date(2026, 9, 1),
            horizonte_meses=0,
        )
        materializar_nomina_fija_trabajador(
            self.trabajador,
            desde_fecha=date(2026, 9, 1),
            horizonte_meses=0,
        )
        obligaciones = ObligacionTrabajador.objects.filter(
            trabajador=self.trabajador,
            periodo_anio=2026,
            periodo_mes=9,
        )
        self.assertEqual(obligaciones.count(), 1)
        obligacion = obligaciones.get()
        self.assertIsNone(obligacion.contrato_id)
        self.assertEqual(obligacion.valor_acordado, Decimal("600.00"))

    def test_concepto_origen_mensualidad_fija(self):
        obligacion = ObligacionTrabajador.objects.create(
            trabajador=self.trabajador,
            contrato=None,
            periodo_anio=2026,
            periodo_mes=9,
            valor_acordado=Decimal("600.00"),
            periodo_servicio_inicio=date(2026, 9, 1),
            periodo_servicio_fin=date(2026, 9, 30),
            fecha_pago_programada=date(2026, 9, 30),
        )
        self.assertEqual(obligacion.concepto_origen, "Mensualidad fija")
