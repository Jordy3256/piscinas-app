from django.test import SimpleTestCase
from django.template.loader import get_template
from pathlib import Path
from django.conf import settings

class AgendasPortalTests(SimpleTestCase):
    def test_plantillas_compilan(self):
        for name in ('mantenimientos', 'proximas_visitas'):
            self.assertIsNotNone(get_template(f'portal_clientes/{name}.html'))

    def test_ambas_vistas_tienen_selector_sin_recarga(self):
        base = Path(settings.BASE_DIR) / 'portal_clientes' / 'templates' / 'portal_clientes'
        for name in ('mantenimientos', 'proximas_visitas'):
            html = (base / f'{name}.html').read_text(encoding='utf8')
            self.assertIn('data-agenda-view="lista"', html)
            self.assertIn('data-agenda-view="calendario"', html)
            self.assertIn('agenda-datos', html)
            self.assertIn('list.hidden=isCal', html)

    def test_proximas_no_tiene_enlace_a_detalle(self):
        base = Path(settings.BASE_DIR) / 'portal_clientes' / 'templates' / 'portal_clientes'
        html = (base / 'proximas_visitas.html').read_text(encoding='utf8')
        self.assertNotIn('mantenimiento_detalle', html)
        self.assertNotIn('Ver visita', html)
