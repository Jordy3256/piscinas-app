from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.test import SimpleTestCase

from dashboard.aquo_ejecutivo import responder_aquo_ejecutivo
from dashboard.centro_decisiones import construir_centro_decisiones


def snapshot_base():
    return {
        "hoy": date(2026, 9, 12), "ciudad": None,
        "rentabilidad": {"margen_pct": 30, "margen": Decimal("300"), "contratos": 10, "en_perdida": 0, "criticos": 0, "atencion": 0, "filas": [], "ranking_ciudades": []},
        "crecimiento": {"actual": {"altas": 1, "recuperados": 0, "bajas": 0, "crecimiento_neto": 1, "retencion": 100, "ingreso_ganado": Decimal("100"), "ingreso_recuperado": Decimal("0"), "ingreso_perdido": Decimal("0")}, "ranking_ciudades": []},
        "salud": {"criticas": 0, "atencion": 0, "avisos": 0, "total_afectados": 0, "items": []},
        "cartera_inteligente": {"total": Decimal("250"), "vencido": Decimal("200"), "recuperable_30": Decimal("100"), "clientes_prioritarios": 1, "ranking": []},
        "operacion": {"cumplimiento": 80.0, "realizados_mes": 8, "programados_mes": 10, "atrasados": 4, "proximos_7": 6, "recurrentes": [], "trabajadores": []},
        "inventario": {"costo_mes": Decimal("50"), "agotados": 1, "criticos": 1, "proximos": 0, "anomalos": 2, "ranking_productos": []},
        "cartera_pendiente": Decimal("250"), "cartera_vencida": Decimal("200"),
        "cobrado_mes": Decimal("500"), "nomina_pendiente": Decimal("0"),
    }


class IntegracionInteligenciaEjecutivaTests(SimpleTestCase):
    @patch("dashboard.aquo_ejecutivo.construir_snapshot_ejecutivo")
    def test_aquo_entiende_operacion_e_inventario(self, mock_snapshot):
        mock_snapshot.return_value = snapshot_base()
        r = responder_aquo_ejecutivo("Compara operación, inventario y cartera")
        self.assertEqual(r["tipo"], "análisis cruzado")
        self.assertIn("operacion", r["intenciones"])
        self.assertIn("inventario", r["intenciones"])
        self.assertIn("cartera", r["intenciones"])

    @patch("dashboard.centro_decisiones.construir_snapshot_ejecutivo")
    def test_centro_decisiones_prioriza_operacion_stock_y_cartera(self, mock_snapshot):
        mock_snapshot.return_value = snapshot_base()
        r = construir_centro_decisiones(hoy=date(2026, 9, 12))
        claves = [x["clave"] for x in r["decisiones"]]
        self.assertIn("cartera_vencida", claves)
        self.assertIn("riesgo_operativo", claves)
        self.assertIn("stock_critico", claves)
        self.assertIn("consumo_anormal", claves)
