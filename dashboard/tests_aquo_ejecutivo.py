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


    @patch("dashboard.aquo_ejecutivo.construir_snapshot_ejecutivo")
    def test_pregunta_multi_area_genera_analisis_cruzado(self, snapshot):
        snapshot.return_value = {
            "rentabilidad": {
                "margen_pct": 20.0, "margen": Decimal("200"), "contratos": 3,
                "en_perdida": 1, "criticos": 1, "atencion": 0,
                "filas": [], "ranking_ciudades": [],
            },
            "crecimiento": {"actual": {
                "altas": 1, "recuperados": 0, "bajas": 2, "crecimiento_neto": -1,
                "retencion": 90.0, "ingreso_ganado": Decimal("100"),
                "ingreso_recuperado": Decimal("0"), "ingreso_perdido": Decimal("200"),
            }, "ranking_ciudades": []},
            "salud": {"criticas": 1, "atencion": 0, "avisos": 0, "total_afectados": 1, "items": []},
            "cartera_pendiente": Decimal("300"), "cartera_vencida": Decimal("150"),
            "cobrado_mes": Decimal("500"), "nomina_pendiente": Decimal("100"),
        }
        r = responder_aquo_ejecutivo(
            "Compara rentabilidad, crecimiento y cartera y dime qué debería priorizar.",
            hoy=date(2026, 9, 12),
        )
        self.assertEqual(r["tipo"], "análisis cruzado")
        self.assertIn("rentabilidad", r["intenciones"])
        self.assertIn("crecimiento", r["intenciones"])
        self.assertIn("cartera", r["intenciones"])
        self.assertTrue(r["detalle"])

    @patch("dashboard.aquo_ejecutivo.construir_snapshot_ejecutivo")
    def test_pregunta_ejecutiva_amplia_devuelve_prioridades(self, snapshot):
        snapshot.return_value = {
            "rentabilidad": {
                "margen_pct": 25.0, "margen": Decimal("250"), "contratos": 4,
                "en_perdida": 0, "criticos": 0, "atencion": 1,
                "filas": [], "ranking_ciudades": [],
            },
            "crecimiento": {"actual": {
                "altas": 2, "recuperados": 0, "bajas": 1, "crecimiento_neto": 1,
                "retencion": 96.0, "ingreso_ganado": Decimal("200"),
                "ingreso_recuperado": Decimal("0"), "ingreso_perdido": Decimal("100"),
            }, "ranking_ciudades": []},
            "salud": {"criticas": 0, "atencion": 1, "avisos": 0, "total_afectados": 1, "items": []},
            "cartera_pendiente": Decimal("100"), "cartera_vencida": Decimal("0"),
            "cobrado_mes": Decimal("500"), "nomina_pendiente": Decimal("0"),
        }
        r = responder_aquo_ejecutivo("¿Cómo está JVAQUA y qué debo hacer?", hoy=date(2026, 9, 12))
        self.assertEqual(r["tipo"], "resumen ejecutivo")
        self.assertTrue(r["detalle"])
