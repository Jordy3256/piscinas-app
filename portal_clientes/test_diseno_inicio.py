from django.test import SimpleTestCase
from django.template.loader import get_template
from django.urls import reverse

class DisenoInicioTest(SimpleTestCase):
    def test_templates_compilan(self):
        self.assertIsNotNone(get_template('portal_clientes/base.html'))
        self.assertIsNotNone(get_template('portal_clientes/inicio.html'))

    def test_ruta_resumen(self):
        self.assertEqual(reverse('portal_clientes:notificaciones_resumen'), '/portal/notificaciones/resumen/')
