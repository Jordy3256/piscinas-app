from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from dashboard.aquo_ejecutivo import responder_aquo_ejecutivo


class AquoEjecutivoTests(TestCase):
    @patch("dashboard.aquo_ejecutivo.construir_snapshot_ejecutivo")
    def test_pregunta_rentabilidad_usa_datos_del_snapshot(self, snapshot):
        snapshot.return_value = {
            "rentabilidad": {
                "margen_pct": 30.0, "margen": Decimal("300"), "contratos": 2,
                "en_perdida": 0, "criticos": 0, "atencion": 0,
                "filas": [], "ranking_ciudades": [],
            },
            "crecimiento": {"actual": {"altas": 0, "recuperados": 0, "bajas": 0, "crecimiento_neto": 0,
                "retencion": 100.0, "ingreso_ganado": Decimal("0"), "ingreso_recuperado": Decimal("0"),
                "ingreso_perdido": Decimal("0")}, "ranking_ciudades": []},
            "salud": {"criticas": 0, "atencion": 0, "avisos": 0, "total_afectados": 0, "incidencias": []},
            "cartera_pendiente": Decimal("0"), "cartera_vencida": Decimal("0"),
            "cobrado_mes": Decimal("0"), "nomina_pendiente": Decimal("0"),
        }
        r = responder_aquo_ejecutivo("¿Cómo está la rentabilidad?", hoy=date(2026, 9, 12))
        self.assertEqual(r["tipo"], "rentabilidad")
        self.assertIn("30.0%", r["respuesta"])
