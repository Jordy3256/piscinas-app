from unittest.mock import Mock, patch
from django.test import RequestFactory, SimpleTestCase
from django.urls import reverse
from .views import digital_centro_aquo_view

class CentroAquoAccesoTests(SimpleTestCase):
    def test_ruta_del_centro(self):
        self.assertIn("/digital/aquo/", reverse("asistente_tecnico:digital_centro_aquo"))

    def test_rechaza_usuario_sin_suscripcion(self):
        request = RequestFactory().get("/digital/aquo/")
        request.user = Mock(is_authenticated=True)
        with patch("asistente_tecnico.views._suscriptor", return_value=None):
            response = digital_centro_aquo_view(request)
        self.assertEqual(response.status_code, 403)
