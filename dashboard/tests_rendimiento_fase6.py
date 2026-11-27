from datetime import date
from django.contrib.auth.models import User
from django.test import TestCase
from clientes.models import Cliente
from trabajadores.models import Trabajador
from mantenimientos.models import Mantenimiento
from dashboard.views import _estadisticas_periodo_operativo


class RendimientoFase6Tests(TestCase):
    def test_periodo_agrupado_con_visitas_compartidas(self):
        cliente = Cliente.objects.create(nombre="Prueba operativo", telefono="0999999999", direccion="Prueba")
        a, b, c = [Trabajador.objects.create(user=User.objects.create_user(username="fase6_" + n)) for n in ("a", "b", "c")]
        hoy = date(2026, 11, 27)
        for estado, equipo in [("realizado", [a,b]), ("pendiente", [a]), ("cancelado", [a,b]), ("pendiente", [b])]:
            m = Mantenimiento.objects.create(cliente=cliente, fecha=hoy, estado=estado)
            m.trabajadores.add(*equipo)
        trabajadores = list(Trabajador.objects.select_related("user").filter(pk__in=[a.pk,b.pk,c.pk]).order_by("pk"))
        qs = Mantenimiento.objects.filter(fecha=hoy).exclude(estado="cancelado")
        for seleccion in (qs, qs.filter(trabajadores=a).distinct()):
            with self.assertNumQueries(1):
                filas = _estadisticas_periodo_operativo(seleccion, trabajadores)
            por_id = {f["id"]: f for f in filas}
            for trabajador in trabajadores:
                original = seleccion.filter(trabajadores=trabajador).distinct()
                total = original.count()
                if not total:
                    self.assertNotIn(trabajador.pk, por_id)
                    continue
                self.assertEqual(por_id[trabajador.pk]["total"], total)
                self.assertEqual(por_id[trabajador.pk]["realizados"], original.filter(estado="realizado").count())
                self.assertEqual(por_id[trabajador.pk]["pendientes"], original.filter(estado="pendiente").count())
