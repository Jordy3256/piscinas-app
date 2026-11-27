from datetime import date
from unittest.mock import patch

from django.test import TestCase

from dashboard.views import _kpis_analitica_pro


class RendimientoFase7Tests(TestCase):
    def test_reutiliza_resumenes_financieros(self):
        hoy = date(2026, 11, 27)
        actual = {"ingresos": 100.0, "egresos": 20.0, "balance": 80.0}
        anterior = {"ingresos": 50.0, "egresos": 10.0, "balance": 40.0}
        with patch("dashboard.views._resumen_financiero_rango") as resumen:
            resultado = _kpis_analitica_pro(hoy, actual, anterior)
        resumen.assert_not_called()
        self.assertEqual(resultado["resumen_mes_actual"], actual)
        self.assertEqual(resultado["resumen_mes_anterior"], anterior)
        self.assertEqual(resultado["total_mantenimientos_mes"], 0)
        self.assertEqual(resultado["mantenimientos_realizados_mes"], 0)
        self.assertEqual(resultado["mantenimientos_pendientes_mes"], 0)
