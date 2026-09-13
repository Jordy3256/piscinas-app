from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from dashboard.centro_decisiones import construir_centro_decisiones


class CentroDecisionesTests(TestCase):
    @patch("dashboard.centro_decisiones.construir_snapshot_ejecutivo")
    def test_prioriza_perdida_y_cartera_vencida(self, snapshot):
        snapshot.return_value = {
            "rentabilidad": {
                "filas": [
                    {"estado": "perdida", "margen": Decimal("-40"), "ingreso": Decimal("100")},
                    {"estado": "critico", "margen": Decimal("10"), "ingreso": Decimal("100")},
                ],
                "en_perdida": 1, "criticos": 1, "atencion": 0, "saludables": 0,
                "margen": Decimal("-30"), "margen_pct": -15.0, "contratos": 2,
                "ranking_ciudades": [], "ranking_trabajadores": [],
            },
            "crecimiento": {
                "actual": {
                    "altas": 0, "recuperados": 0, "bajas": 1, "crecimiento_neto": -1,
                    "retencion": 90.0, "ingreso_ganado": Decimal("0"),
                    "ingreso_recuperado": Decimal("0"), "ingreso_perdido": Decimal("100"),
                },
                "ranking_ciudades": [],
            },
            "salud": {
                "criticas": 1, "atencion": 0, "avisos": 0,
                "total_afectados": 1, "items": [],
            },
            "cartera_vencida": Decimal("250"),
            "cartera_pendiente": Decimal("250"),
            "cobrado_mes": Decimal("500"),
            "nomina_pendiente": Decimal("0"),
        }
        r = construir_centro_decisiones(hoy=date(2026, 9, 12))
        self.assertGreaterEqual(r["criticas"], 3)
        self.assertEqual(r["decisiones"][0]["clave"], "contratos_en_perdida")
        self.assertEqual(r["impacto_riesgo"], Decimal("145.00"))
        self.assertEqual(r["capital_gestionar"], Decimal("250.00"))

    @patch("dashboard.centro_decisiones.construir_snapshot_ejecutivo")
    def test_sin_riesgos_devuelve_estado_saludable(self, snapshot):
        snapshot.return_value = {
            "rentabilidad": {
                "filas": [], "en_perdida": 0, "criticos": 0, "atencion": 0,
                "saludables": 0, "margen": Decimal("0"), "margen_pct": 0.0,
                "contratos": 0, "ranking_ciudades": [], "ranking_trabajadores": [],
            },
            "crecimiento": {
                "actual": {
                    "altas": 0, "recuperados": 0, "bajas": 0, "crecimiento_neto": 0,
                    "retencion": 100.0, "ingreso_ganado": Decimal("0"),
                    "ingreso_recuperado": Decimal("0"), "ingreso_perdido": Decimal("0"),
                },
                "ranking_ciudades": [],
            },
            "salud": {
                "criticas": 0, "atencion": 0, "avisos": 0,
                "total_afectados": 0, "items": [],
            },
            "cartera_vencida": Decimal("0"), "cartera_pendiente": Decimal("0"),
            "cobrado_mes": Decimal("0"), "nomina_pendiente": Decimal("0"),
        }
        r = construir_centro_decisiones(hoy=date(2026, 9, 12))
        self.assertEqual(r["estado"], "saludable")
        self.assertEqual(r["total"], 0)
