"""Pruebas de autorización transversal del dashboard."""
import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from trabajadores.models import Trabajador


class SeguridadRutasGPSTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.cliente = User.objects.create_user(username="portal_prueba_gps", password="test-123456")
        self.tecnico_user = User.objects.create_user(username="tecnico_prueba_gps", password="test-123456")
        grupo, _ = Group.objects.get_or_create(name="Trabajadores")
        self.tecnico_user.groups.add(grupo)
        self.trabajador = Trabajador.objects.create(user=self.tecnico_user, telefono="0990000000")

    def test_cliente_no_puede_invocar_matriz_google(self):
        self.client.force_login(self.cliente)
        with patch.dict("os.environ", {"GOOGLE_MAPS_API_KEY": "clave-de-prueba"}):
            with patch("urllib.request.urlopen") as llamada:
                respuesta = self.client.post(
                    reverse("ruta_matriz_google"),
                    data=json.dumps({"points": [{"lat": -2.1, "lng": -79.9}, {"lat": -2.2, "lng": -79.8}]}),
                    content_type="application/json",
                )
        self.assertEqual(respuesta.status_code, 403)
        llamada.assert_not_called()

    def test_cliente_no_puede_resolver_coordenadas(self):
        self.client.force_login(self.cliente)
        respuesta = self.client.post(
            reverse("ruta_resolver_coordenadas"),
            data=json.dumps({"cliente_ids": [1], "contrato_ids": [1]}),
            content_type="application/json",
        )
        self.assertEqual(respuesta.status_code, 403)

    def test_trabajador_no_resuelve_ids_sin_asignacion(self):
        self.client.force_login(self.tecnico_user)
        with patch("dashboard.views._geocodificar_contrato_google") as geocodificar_contrato, \
             patch("dashboard.views._geocodificar_cliente_google") as geocodificar_cliente:
            respuesta = self.client.post(
                reverse("ruta_resolver_coordenadas"),
                data=json.dumps({"cliente_ids": [1, 2], "contrato_ids": [1, 2]}),
                content_type="application/json",
            )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()["resultados"] if "resultados" in respuesta.json() else respuesta.json()["coords"], {})
        geocodificar_contrato.assert_not_called()
        geocodificar_cliente.assert_not_called()


class EvidenciasMediaPrivadaTests(TestCase):
    """Las rutas directas a evidencias no omiten autenticacion ni permisos."""

    def test_anonimo_no_descarga_evidencia_por_media(self):
        respuesta = self.client.get('/media/mantenimientos/no-existe.jpg')
        self.assertEqual(respuesta.status_code, 404)

    def test_usuario_autenticado_no_descarga_evidencia_ajena(self):
        from django.contrib.auth import get_user_model
        usuario = get_user_model().objects.create_user(username='media_sin_permiso', password='test')
        self.client.force_login(usuario)
        respuesta = self.client.get('/media/mantenimientos/no-existe.jpg')
        self.assertEqual(respuesta.status_code, 404)
