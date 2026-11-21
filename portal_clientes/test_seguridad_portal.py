"""Pruebas de aislamiento de conversaciones y archivos del Portal JVAQUA.

Ejecutar: python manage.py test portal_clientes.test_seguridad_portal
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from clientes.models import Cliente
from portal_clientes.models import AccesoCliente, ConversacionSoporte, MensajeSoporte


class AislamientoSoporteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.usuario_a = User.objects.create_user(username='portal_test_a', password='test-a-strong-password')
        cls.usuario_b = User.objects.create_user(username='portal_test_b', password='test-b-strong-password')
        cls.cliente_a = Cliente.objects.create(nombre='Cliente Prueba A', telefono='0001', direccion='Prueba A')
        cls.cliente_b = Cliente.objects.create(nombre='Cliente Prueba B', telefono='0002', direccion='Prueba B')
        AccesoCliente.objects.create(cliente=cls.cliente_a, usuario=cls.usuario_a, habilitado=True)
        AccesoCliente.objects.create(cliente=cls.cliente_b, usuario=cls.usuario_b, habilitado=True)
        cls.chat_b = ConversacionSoporte.objects.create(cliente=cls.cliente_b)
        cls.mensaje_b = MensajeSoporte.objects.create(
            conversacion=cls.chat_b, autor=cls.usuario_b, es_cliente=True,
            contenido='Privado', archivo=b'\xff\xd8\xff', archivo_clase='foto', archivo_tipo='image/jpeg'
        )

    def test_cliente_no_puede_abrir_chat_ajeno(self):
        self.client.force_login(self.usuario_a)
        url = reverse('portal_clientes:soporte_conversacion', args=[self.chat_b.pk])
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.post(url, {'mensaje': 'No autorizado'}).status_code, 404)
        self.assertEqual(MensajeSoporte.objects.filter(conversacion=self.chat_b).count(), 1)

    def test_cliente_no_puede_leer_archivo_ajeno(self):
        self.client.force_login(self.usuario_a)
        url = reverse('portal_clientes:soporte_archivo', args=[self.mensaje_b.pk])
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_cliente_no_puede_leer_actualizaciones_ajenas(self):
        self.client.force_login(self.usuario_a)
        url = reverse('portal_clientes:soporte_actualizaciones', args=[self.chat_b.pk])
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_cliente_no_puede_usar_modo_administrador(self):
        self.client.force_login(self.usuario_a)
        url = reverse('portal_clientes:soporte_actualizaciones', args=[self.chat_b.pk])
        self.assertEqual(self.client.get(url, {'lado': 'admin'}).status_code, 403)
        self.assertEqual(self.client.get(reverse('portal_clientes:soporte_contadores'), {'lado': 'admin'}).status_code, 403)

    def test_cliente_propietario_puede_abrir_su_chat_y_archivo(self):
        self.client.force_login(self.usuario_b)
        self.assertEqual(self.client.get(reverse('portal_clientes:soporte_conversacion', args=[self.chat_b.pk])).status_code, 200)
        respuesta = self.client.get(reverse('portal_clientes:soporte_archivo', args=[self.mensaje_b.pk]))
        self.assertEqual(respuesta.status_code, 200)
        directivas_cache = {parte.strip().lower() for parte in respuesta['Cache-Control'].split(',')}
        self.assertIn('private', directivas_cache)
        self.assertIn('no-store', directivas_cache)

    def test_acceso_deshabilitado_bloquea_chat_y_archivos(self):
        AccesoCliente.objects.filter(cliente=self.cliente_b).update(habilitado=False)
        self.client.force_login(self.usuario_b)
        self.assertEqual(self.client.get(reverse('portal_clientes:soporte_archivo', args=[self.mensaje_b.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse('portal_clientes:soporte_actualizaciones', args=[self.chat_b.pk])).status_code, 403)

class AislamientoNotificacionesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from portal_clientes.models import AvisoPortal
        User = get_user_model()
        cls.usuario_a = User.objects.create_user(username='avisos_test_a', password='test-a-strong-password')
        cls.usuario_b = User.objects.create_user(username='avisos_test_b', password='test-b-strong-password')
        cls.cliente_a = Cliente.objects.create(nombre='Avisos A', telefono='001', direccion='A')
        cls.cliente_b = Cliente.objects.create(nombre='Avisos B', telefono='002', direccion='B')
        AccesoCliente.objects.create(cliente=cls.cliente_a, usuario=cls.usuario_a, habilitado=True)
        AccesoCliente.objects.create(cliente=cls.cliente_b, usuario=cls.usuario_b, habilitado=True)
        cls.aviso_b = AvisoPortal.objects.create(cliente=cls.cliente_b, clave='comunicado:seguridad-b', tipo='comunicado', titulo='Privado B', detalle='Solo B')

    def test_no_puede_abrir_aviso_ajeno(self):
        self.client.force_login(self.usuario_a)
        url = reverse('portal_clientes:notificacion_general_abrir', args=[self.aviso_b.pk])
        self.assertEqual(self.client.post(url).status_code, 404)
        self.aviso_b.refresh_from_db()
        self.assertIsNone(self.aviso_b.leida_en)

    def test_contador_no_incluye_avisos_ajenos(self):
        self.client.force_login(self.usuario_a)
        respuesta = self.client.get(reverse('portal_clientes:notificaciones_contador'))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()['total'], 0)
