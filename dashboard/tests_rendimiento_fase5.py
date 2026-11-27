from datetime import date, timedelta
from decimal import Decimal
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from clientes.models import Cliente
from contratos.models import Contrato
from trabajadores.models import Trabajador
from mantenimientos.models import Mantenimiento
from finanzas.models import Ingreso, Egreso
from dashboard.views import (_build_serie_financiera_meses, _build_serie_operativa_meses,
                             _estadisticas_trabajadores)


class RendimientoFase5Tests(TestCase):
    def test_series_financieras_agrupadas(self):
        Ingreso.objects.create(concepto='Prueba', total=Decimal('100.50'), fecha=date(2026, 1, 5))
        Egreso.objects.create(concepto='Prueba', cantidad=2, costo_unitario=Decimal('10.25'), fecha=date(2026, 1, 6))
        with self.assertNumQueries(2):
            serie = _build_serie_financiera_meses(date(2026, 2, 1), 3)
        self.assertEqual(serie, {'labels': ['12/2025', '01/2026', '02/2026'],
                                 'ingresos': [0., 100.5, 0.], 'egresos': [0., 20.5, 0.],
                                 'balance': [0., 80., 0.]})

    def test_series_y_trabajadores_compartidos(self):
        hoy = timezone.localdate()
        inicio = hoy.replace(day=1)
        cliente = Cliente.objects.create(nombre='Prueba SQL', telefono='0999999999', direccion='Prueba')
        contrato = Contrato.objects.create(cliente=cliente, frecuencia='1_semanal', forma_pago='adelantado',
            precio_mensual=Decimal('100'), valor_tecnico_mensual=Decimal('20'), fecha_inicio=inicio, fecha_inicio_original=inicio)
        a, b, c = [Trabajador.objects.create(user=User.objects.create_user(username='sql5_'+n)) for n in ('a','b','c')]
        # Eliminar posibles visitas automáticas creadas por señales del contrato.
        Mantenimiento.objects.filter(contrato=contrato).delete()
        for estado, equipo in [('realizado', [a,b]), ('pendiente', [a]), ('cancelado', [b])]:
            m = Mantenimiento.objects.create(cliente=cliente, contrato=contrato, fecha=hoy, estado=estado)
            m.trabajadores.add(*equipo)
        with self.assertNumQueries(1):
            serie = _build_serie_operativa_meses(hoy, 1)
        self.assertEqual(serie['realizados'], [1])
        self.assertEqual(serie['pendientes'], [1])
        self.assertEqual(serie['atrasados'], [0])
        with self.assertNumQueries(5):
            datos = _estadisticas_trabajadores([a,b,c], inicio, hoy)
        for t in (a,b,c):
            qs = Mantenimiento.objects.filter(trabajadores=t, fecha__range=(inicio,hoy))
            self.assertEqual(datos[t.pk]['mantenimientos_programados'], qs.count())
            self.assertEqual(datos[t.pk]['mantenimientos_mes'], qs.filter(estado='realizado').count())
            self.assertEqual(datos[t.pk]['mantenimientos_pendientes'], qs.exclude(estado='realizado').count())
            self.assertEqual(datos[t.pk]['mantenimientos_atrasados'], qs.filter(fecha__lt=hoy).exclude(estado='realizado').count())
        self.assertEqual(datos[c.pk]['pagos_mes'], Decimal('0.00'))
        with self.assertNumQueries(0):
            self.assertEqual(_estadisticas_trabajadores([], inicio, hoy), {})
