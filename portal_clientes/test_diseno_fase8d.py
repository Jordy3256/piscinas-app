from django.test import SimpleTestCase
from django.template.loader import get_template


class DisenoFase8DTests(SimpleTestCase):
    def test_plantillas_cargan(self):
        for nombre in ("mis_pagos.html", "mi_contrato.html", "soporte_lista.html", "soporte_chat.html"):
            with self.subTest(nombre=nombre):
                self.assertIsNotNone(get_template("portal_clientes/" + nombre))

    def test_pagos_sin_explicacion_tecnica(self):
        plantilla = get_template("portal_clientes/mis_pagos.html")
        self.assertNotIn("Se muestra una sola próxima factura", plantilla.template.source)

    def test_contrato_sin_numero_interno(self):
        plantilla = get_template("portal_clientes/mi_contrato.html")
        self.assertNotIn("Contrato #{{ contrato.pk }}", plantilla.template.source)
