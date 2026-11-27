"""Fase 9F: barreras de regresión antes de retirar código comercial legado.

Estas pruebas no eliminan datos ni requieren migraciones.
"""
from io import StringIO

from django.core.management import call_command
from django.test import SimpleTestCase
from django.urls import resolve, reverse

from .urls import plataforma_digital_retirada


class SeparacionFase9FTests(SimpleTestCase):
    def test_todas_las_rutas_comerciales_y_soporte_antiguo_estan_retiradas(self):
        from .urls import urlpatterns

        antiguas = [
            patron for patron in urlpatterns
            if str(patron.pattern).startswith('digital/')
            or str(patron.pattern).startswith('administracion/avisos-digitales/')
            or str(patron.pattern).startswith('administracion/comprobante/')
            or str(patron.pattern).startswith('administracion/suscripciones-digitales/')
            or str(patron.pattern).startswith('administracion/soporte/')
            or str(patron.pattern).startswith('administracion/soporte-burbuja/')
        ]
        self.assertGreaterEqual(len(antiguas), 35)
        for patron in antiguas:
            with self.subTest(ruta=str(patron.pattern)):
                self.assertIs(patron.callback, plataforma_digital_retirada)

    def test_rutas_heredadas_no_aceptan_solicitudes_get_ni_post(self):
        for nombre, argumentos in (
            ('digital_registro', ()),
            ('digital_acceso', ()),
            ('digital_cobro_pago', (1,)),
            ('digital_push_suscribir', ()),
            ('soporte_admin_mensajes_api', (1,)),
        ):
            ruta = reverse('asistente_tecnico:' + nombre, args=argumentos)
            for metodo in (self.client.get, self.client.post):
                with self.subTest(nombre=nombre, metodo=metodo.__name__):
                    respuesta = metodo(ruta)
                    self.assertEqual(respuesta.status_code, 410)
                    self.assertIn('no-store', respuesta['Cache-Control'])

    def test_comandos_comerciales_antiguos_no_generan_cobros(self):
        for nombre in ('procesar_recordatorios_aquo', 'generar_recordatorios_cobros_aquo'):
            with self.subTest(comando=nombre):
                salida = StringIO()
                call_command(nombre, stdout=salida)
                self.assertIn('retirado', salida.getvalue().lower())

    def test_rutas_tecnicas_permanecen_activas_en_el_enrutador(self):
        for nombre in ('inicio', 'biblioteca', 'academia', 'cms_admin'):
            with self.subTest(nombre=nombre):
                ruta = reverse('asistente_tecnico:' + nombre)
                self.assertIsNot(resolve(ruta).func, plataforma_digital_retirada)
