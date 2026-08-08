from django.test import SimpleTestCase
from .engine import calcular_recomendacion


class MotorJVAQUATests(SimpleTestCase):
    def test_agua_verde_32m3_ph_alto_usa_dos_kg_sulfato_sin_reductor(self):
        r = calcular_recomendacion(32, 8.0, 0.2, "verde", "residencial")
        self.assertEqual(r["tipo_tratamiento"], "floculacion")
        productos = {x["clave"]: x for x in r["productos_sugeridos"]}
        self.assertEqual(productos["sulfato_aluminio"]["cantidad"], 2)
        self.assertNotIn("reductor_ph", productos)

    def test_floculacion_ph_bajo_recomienda_p24(self):
        r = calcular_recomendacion(25, 6.8, 0.5, "muy_turbia", "residencial")
        claves = {x["clave"] for x in r["productos_sugeridos"]}
        self.assertIn("p24", claves)
        self.assertIn("sulfato_aluminio", claves)

    def test_turbidez_ligera_no_recomienda_sulfato(self):
        r = calcular_recomendacion(30, 7.3, 0.4, "ligeramente_turbia", "residencial")
        claves = {x["clave"] for x in r["productos_sugeridos"]}
        self.assertEqual(r["tipo_tratamiento"], "correctivo")
        self.assertNotIn("sulfato_aluminio", claves)
        self.assertIn("cloro_granulado", claves)

    def test_transparente_residencial_prioriza_tricloro(self):
        r = calcular_recomendacion(40, 7.4, 0.8, "transparente", "residencial")
        claves = {x["clave"] for x in r["productos_sugeridos"]}
        self.assertIn("tricloro", claves)
