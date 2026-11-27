from datetime import date
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from finanzas.facturacion_externa import sincronizar_avisos_facturacion
from finanzas.models import AvisoFacturacion
from finanzas import tests_pago_por_visita


class RendimientoFacturacionTests(TestCase):
    setUp = tests_pago_por_visita.PagoPorVisitaTests.setUp

    def test_sincronizacion_estable_sin_escrituras(self):
        visita = self.visitas[0]
        visita.estado = "realizado"
        visita.save(update_fields=["estado"])
        opciones = dict(hoy=date(2026, 9, 4), meses_atras=0, meses_adelante=0)
        primero = sincronizar_avisos_facturacion(**opciones)
        self.assertEqual(primero["errores"], [])
        self.assertEqual(AvisoFacturacion.objects.filter(contrato=self.contrato).count(), 1)
        with CaptureQueriesContext(connection) as consultas:
            segundo = sincronizar_avisos_facturacion(**opciones)
        self.assertEqual(segundo, dict(creados=0, actualizados=0, anulados=0, errores=[]))
        escrituras = [q["sql"] for q in consultas if q["sql"].lstrip().upper().startswith(("UPDATE ", "INSERT ", "DELETE "))]
        self.assertEqual(escrituras, [])
