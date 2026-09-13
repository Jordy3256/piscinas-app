from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from clientes.models import Cliente
from contratos.models import Contrato
from mantenimientos.models import Mantenimiento
from trabajadores.models import Trabajador
from dashboard.inteligencia_operativa import analizar_operacion


class InteligenciaOperativaTests(TestCase):
    def test_detecta_mantenimiento_atrasado_y_cumplimiento(self):
        hoy = date(2026, 9, 12)
        user = User.objects.create_user(username="tecnico-op")
        trabajador = Trabajador.objects.create(user=user, telefono="0999999999")
        cliente = Cliente.objects.create(nombre="Cliente operativo", telefono="0988888888", direccion="Prueba")
        contrato = Contrato.objects.create(
            cliente=cliente, frecuencia="1_semanal", forma_pago="adelantado",
            precio_mensual=Decimal("100.00"), valor_tecnico_mensual=Decimal("20.00"),
            fecha_inicio=date(2026, 9, 1), fecha_inicio_original=date(2026, 9, 1),
        )
        m = Mantenimiento.objects.create(
            cliente=cliente, contrato=contrato, fecha=hoy-timedelta(days=3), estado="pendiente",
        )
        m.trabajadores.add(trabajador)
        Mantenimiento.objects.create(
            cliente=cliente, contrato=contrato, fecha=hoy-timedelta(days=1), estado="realizado",
        ).trabajadores.add(trabajador)

        r = analizar_operacion(hoy=hoy)
        self.assertEqual(r["atrasados"], 1)
        self.assertEqual(r["programados_mes"], 2)
        self.assertEqual(r["realizados_mes"], 1)
        self.assertEqual(r["cumplimiento"], 50.0)
        self.assertTrue(r["riesgos"])
