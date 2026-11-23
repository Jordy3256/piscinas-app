"""Regresiones de privacidad y operaciones del Portal de Clientes, fase 8F."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from clientes.models import Cliente
from .models import AccesoCliente, AvisoPortal, ConversacionSoporte
from .notificaciones import _generales


class AuditoriaPortal8FTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.ua = User.objects.create_user(username='auditoria8f_a', password='pass-a-fuerte')
        cls.ub = User.objects.create_user(username='auditoria8f_b', password='pass-b-fuerte')
        cls.ca = Cliente.objects.create(nombre='Auditoría A', telefono='100', direccion='A')
        cls.cb = Cliente.objects.create(nombre='Auditoría B', telefono='200', direccion='B')
        AccesoCliente.objects.create(cliente=cls.ca, usuario=cls.ua, habilitado=True)
        AccesoCliente.objects.create(cliente=cls.cb, usuario=cls.ub, habilitado=True)

    def test_no_elimina_notificaciones_ajenas(self):
        aviso = AvisoPortal.objects.create(cliente=self.cb, clave='comunicado:8f:b', tipo='comunicado', titulo='Privado', detalle='B')
        self.client.force_login(self.ua)
        url = reverse('portal_clientes:notificacion_eliminar', args=['general', aviso.pk])
        self.assertEqual(self.client.post(url).status_code, 404)
        aviso.refresh_from_db()
        self.assertEqual(aviso.tipo, 'comunicado')

    def test_eliminar_requiere_post(self):
        aviso = AvisoPortal.objects.create(cliente=self.ca, clave='comunicado:8f:a', tipo='comunicado', titulo='Propio', detalle='A')
        self.client.force_login(self.ua)
        self.assertEqual(self.client.get(reverse('portal_clientes:notificacion_eliminar', args=['general', aviso.pk])).status_code, 405)
        self.assertEqual(self.client.get(reverse('portal_clientes:notificaciones_eliminar_todas')).status_code, 405)
        aviso.refresh_from_db()
        self.assertEqual(aviso.tipo, 'comunicado')

    def test_aviso_eliminado_no_reaparece_en_listado(self):
        aviso = AvisoPortal.objects.create(cliente=self.ca, clave='comunicado:8f:oculto', tipo='comunicado', titulo='Propio', detalle='A')
        self.client.force_login(self.ua)
        self.assertEqual(self.client.post(reverse('portal_clientes:notificacion_eliminar', args=['general', aviso.pk])).status_code, 302)
        self.assertFalse(_generales(self.ca.pk).filter(pk=aviso.pk).exists())
        aviso.refresh_from_db()
        self.assertEqual(aviso.clave, 'comunicado:8f:oculto')

    def test_soporte_abre_una_conversacion_y_no_acepta_post_en_entrada(self):
        self.client.force_login(self.ua)
        url = reverse('portal_clientes:soporte')
        self.assertEqual(self.client.get(url).status_code, 302)
        self.assertEqual(self.client.get(url).status_code, 302)
        self.assertEqual(ConversacionSoporte.objects.filter(cliente=self.ca).count(), 1)
        self.assertEqual(self.client.post(url, {'mensaje': 'No debe publicarse aquí'}).status_code, 405)

    def test_soporte_ajeno_no_accesible(self):
        chat = ConversacionSoporte.objects.create(cliente=self.cb)
        self.client.force_login(self.ua)
        self.assertEqual(self.client.get(reverse('portal_clientes:soporte_conversacion', args=[chat.pk])).status_code, 404)

    def test_acceso_desactivado_no_ve_notificaciones(self):
        AccesoCliente.objects.filter(cliente=self.ca).update(habilitado=False)
        self.client.force_login(self.ua)
        self.assertEqual(self.client.get(reverse('portal_clientes:notificaciones_resumen')).status_code, 404)
