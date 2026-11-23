"""Pruebas del acceso compartido sin cruce de roles."""
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.test import TestCase
from django.utils import timezone
from clientes.models import Cliente
from portal_clientes.models import AccesoCliente


class AccesoUnificadoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cliente = Cliente.objects.create(nombre='Cliente Login', telefono='099999', direccion='Prueba', email='cliente@example.com')
        cls.acceso = AccesoCliente.objects.create(cliente=cls.cliente, habilitado=True)
        cls.personal = get_user_model().objects.create_user(username='tecnico_prueba', password='Password-Equipo-2026!', is_staff=True)

    def test_codigo_inicia_activacion_y_no_autentica(self):
        self.acceso.codigo_hash = make_password('CodigoTemporalMuySeguro')
        self.acceso.codigo_expira = timezone.now() + timedelta(hours=1)
        self.acceso.save()
        respuesta = self.client.post('/login/', {'username':'cliente@example.com', 'password':'CodigoTemporalMuySeguro'})
        self.assertRedirects(respuesta, '/portal/activar/', fetch_redirect_response=False)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_activacion_y_login_correo(self):
        self.acceso.codigo_hash = make_password('CodigoTemporalMuySeguro')
        self.acceso.codigo_expira = timezone.now() + timedelta(hours=1)
        self.acceso.save()
        self.client.post('/login/', {'username':'cliente@example.com', 'password':'CodigoTemporalMuySeguro'})
        respuesta = self.client.post('/portal/activar/', {'password':'ClaveSeguraParaCliente-2026!', 'confirmacion':'ClaveSeguraParaCliente-2026!'})
        self.assertRedirects(respuesta, '/login/', fetch_redirect_response=False)
        respuesta = self.client.post('/login/', {'username':'cliente@example.com', 'password':'ClaveSeguraParaCliente-2026!'})
        self.assertRedirects(respuesta, '/portal/inicio/', fetch_redirect_response=False)
        self.assertEqual(self.client.get('/dashboard/inicio/').status_code, 403)
        self.assertEqual(self.client.get('/admin/').status_code, 403)

    def test_personal_sigue_ingresando_con_usuario(self):
        respuesta = self.client.post('/login/', {'username':'tecnico_prueba', 'password':'Password-Equipo-2026!'})
        self.assertRedirects(respuesta, '/dashboard/inicio/', fetch_redirect_response=False)

    def test_usuario_sin_rol_no_puede_ingresar_al_dashboard(self):
        usuario = get_user_model().objects.create_user(username='sin_rol_prueba', password='ClavePrueba-2026!')
        respuesta = self.client.post('/login/', {'username': usuario.username, 'password': 'ClavePrueba-2026!'})
        self.assertEqual(respuesta.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_codigo_caducado_no_activa(self):
        self.acceso.codigo_hash = make_password('CodigoTemporalMuySeguro')
        self.acceso.codigo_expira = timezone.now() - timedelta(seconds=1)
        self.acceso.save()
        respuesta = self.client.post('/login/', {'username':'cliente@example.com', 'password':'CodigoTemporalMuySeguro'})
        self.assertEqual(respuesta.status_code, 200)
        self.assertNotIn('portal_activacion_id', self.client.session)
