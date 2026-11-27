"""Pruebas negativas de descarga de evidencias de órdenes de trabajo."""
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.http import Http404
from django.test import RequestFactory, SimpleTestCase

from backend.urls import archivo_orden_trabajo_privado


class ArchivosOrdenTrabajoPrivadosTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_anonimo_no_descarga_foto(self):
        request = self.factory.get('/media/ordenes_trabajo/foto.jpg')
        request.user = AnonymousUser()
        with self.assertRaises(Http404):
            archivo_orden_trabajo_privado(request, 'foto.jpg')

    def test_anonimo_no_descarga_comprobante(self):
        request = self.factory.get('/media/ordenes_trabajo/comprobantes/recibo.pdf')
        request.user = AnonymousUser()
        with self.assertRaises(Http404):
            archivo_orden_trabajo_privado(request, 'comprobantes/recibo.pdf')

    def test_usuario_ajeno_no_descarga_foto(self):
        request = self.factory.get('/media/ordenes_trabajo/foto.jpg')
        request.user = SimpleNamespace(is_authenticated=True, is_staff=False, is_superuser=False)
        orden = SimpleNamespace(trabajador_id=42)
        foto = SimpleNamespace(orden=orden, imagen=SimpleNamespace())
        with patch('ordenes_trabajo.views._es_admin', return_value=False), \
             patch('ordenes_trabajo.models.FotoOrdenTrabajo.objects') as fotos, \
             patch('trabajadores.models.Trabajador.objects') as trabajadores:
            fotos.select_related.return_value.filter.return_value.first.return_value = foto
            trabajadores.filter.return_value.exists.return_value = False
            with self.assertRaises(Http404):
                archivo_orden_trabajo_privado(request, 'foto.jpg')

    def test_usuario_ajeno_no_descarga_comprobante(self):
        request = self.factory.get('/media/ordenes_trabajo/comprobantes/recibo.pdf')
        request.user = SimpleNamespace(is_authenticated=True, is_staff=False, is_superuser=False)
        orden = SimpleNamespace(trabajador_id=42, cobro_comprobante=SimpleNamespace())
        with patch('ordenes_trabajo.views._es_admin', return_value=False), \
             patch('ordenes_trabajo.models.OrdenTrabajo.objects') as ordenes, \
             patch('trabajadores.models.Trabajador.objects') as trabajadores:
            ordenes.filter.return_value.first.return_value = orden
            trabajadores.filter.return_value.exists.return_value = False
            with self.assertRaises(Http404):
                archivo_orden_trabajo_privado(request, 'comprobantes/recibo.pdf')

class ArchivosOrdenTrabajoAutorizadosTests(SimpleTestCase):
    """Verifica la descarga legítima, además de los bloqueos existentes."""

    def setUp(self):
        self.factory = RequestFactory()
        self.usuario = SimpleNamespace(is_authenticated=True, is_staff=False, is_superuser=False)

    def _descargar(self, path, admin=False, asignado=False):
        from io import BytesIO
        request = self.factory.get('/media/ordenes_trabajo/' + path)
        request.user = self.usuario
        orden = SimpleNamespace(trabajador_id=42)
        archivo = SimpleNamespace(open=lambda mode: BytesIO(b'archivo de prueba'))
        with patch('ordenes_trabajo.views._es_admin', return_value=admin), \
             patch('ordenes_trabajo.models.FotoOrdenTrabajo.objects') as fotos, \
             patch('ordenes_trabajo.models.OrdenTrabajo.objects') as ordenes, \
             patch('trabajadores.models.Trabajador.objects') as trabajadores:
            fotos.select_related.return_value.filter.return_value.first.return_value = SimpleNamespace(orden=orden, imagen=archivo)
            ordenes.filter.return_value.first.return_value = SimpleNamespace(trabajador_id=42, cobro_comprobante=archivo)
            trabajadores.filter.return_value.exists.return_value = asignado
            respuesta = archivo_orden_trabajo_privado(request, path)
            self.assertEqual(respuesta.status_code, 200)
            self.assertEqual(b''.join(respuesta.streaming_content), b'archivo de prueba')
            self.assertIn('no-store', respuesta['Cache-Control'])
            self.assertEqual(respuesta['X-Content-Type-Options'], 'nosniff')

    def test_admin_descarga_foto(self):
        self._descargar('foto.jpg', admin=True)

    def test_admin_descarga_comprobante(self):
        self._descargar('comprobantes/recibo.pdf', admin=True)

    def test_trabajador_asignado_descarga_foto(self):
        self._descargar('foto.jpg', asignado=True)

    def test_trabajador_asignado_descarga_comprobante(self):
        self._descargar('comprobantes/recibo.pdf', asignado=True)
