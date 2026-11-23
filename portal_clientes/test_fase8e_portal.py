"""Regresiones Fase 8E: privacidad, ocultación y chat único."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from clientes.models import Cliente
from portal_clientes.models import AccesoCliente, AvisoPortal, ConversacionSoporte, MensajeSoporte
from portal_clientes.notificaciones import _generales


class PortalFase8ETests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.a = User.objects.create_user(username='fase8e_a', password='test-pass-strong')
        cls.b = User.objects.create_user(username='fase8e_b', password='test-pass-strong')
        cls.ca = Cliente.objects.create(nombre='Cliente A', telefono='001', direccion='A')
        cls.cb = Cliente.objects.create(nombre='Cliente B', telefono='002', direccion='B')
        AccesoCliente.objects.create(cliente=cls.ca, usuario=cls.a, habilitado=True)
        AccesoCliente.objects.create(cliente=cls.cb, usuario=cls.b, habilitado=True)

    def test_eliminar_aviso_propio_sin_recrear_ni_afectar_otros(self):
        propio = AvisoPortal.objects.create(cliente=self.ca, clave='comunicado:1', tipo='comunicado', titulo='Aviso A', detalle='A')
        ajeno = AvisoPortal.objects.create(cliente=self.cb, clave='comunicado:2', tipo='comunicado', titulo='Aviso B', detalle='B')
        self.client.force_login(self.a)
        self.assertEqual(self.client.post(reverse('portal_clientes:notificacion_eliminar', args=['general', ajeno.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse('portal_clientes:notificacion_eliminar', args=['general', propio.pk])).status_code, 302)
        self.assertFalse(_generales(self.ca.pk).filter(pk=propio.pk).exists())
        self.assertTrue(_generales(self.cb.pk).filter(pk=ajeno.pk).exists())
        propio.refresh_from_db()
        self.assertEqual(propio.tipo, 'oculta')

    def test_eliminar_todas_solo_cliente_actual(self):
        AvisoPortal.objects.create(cliente=self.ca, clave='comunicado:a', tipo='comunicado', titulo='A', detalle='A')
        AvisoPortal.objects.create(cliente=self.cb, clave='comunicado:b', tipo='comunicado', titulo='B', detalle='B')
        self.client.force_login(self.a)
        self.assertEqual(self.client.post(reverse('portal_clientes:notificaciones_eliminar_todas')).status_code, 302)
        self.assertFalse(_generales(self.ca.pk).exists())
        self.assertEqual(_generales(self.cb.pk).count(), 1)

    def test_soporte_directo_y_conserva_historial_de_varios_chats(self):
        primero = ConversacionSoporte.objects.create(cliente=self.ca)
        segundo = ConversacionSoporte.objects.create(cliente=self.ca)
        MensajeSoporte.objects.create(conversacion=primero, autor=self.a, es_cliente=True, contenido='Uno')
        MensajeSoporte.objects.create(conversacion=segundo, autor=self.a, es_cliente=True, contenido='Dos')
        self.client.force_login(self.a)
        response = self.client.get(reverse('portal_clientes:soporte'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ConversacionSoporte.objects.filter(cliente=self.ca).count(), 1)
        self.assertEqual(MensajeSoporte.objects.filter(conversacion__cliente=self.ca).count(), 2)
        self.assertIn(str(primero.pk), response['Location'])

    def test_soporte_no_crea_conversaciones_duplicadas(self):
        self.client.force_login(self.a)
        self.client.get(reverse('portal_clientes:soporte'))
        self.client.get(reverse('portal_clientes:soporte'))
        self.assertEqual(ConversacionSoporte.objects.filter(cliente=self.ca).count(), 1)
