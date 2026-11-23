"""Pruebas aisladas del comando diario, sin tocar cartera real."""
from datetime import date
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase


class CronAvisosTests(SimpleTestCase):
    @patch('portal_clientes.management.commands.generar_avisos_cobro_portal.AccesoCliente')
    @patch('portal_clientes.management.commands.generar_avisos_cobro_portal._sincronizar_cobros')
    def test_fecha_ecuador_y_resumen(self, sincronizar, acceso):
        acceso.objects.filter.return_value.values_list.return_value.distinct.return_value.iterator.return_value = [11, 12]
        sincronizar.return_value = 1
        salida = StringIO()
        with patch('portal_clientes.management.commands.generar_avisos_cobro_portal.timezone.localdate', return_value=date(2026, 11, 22)):
            call_command('generar_avisos_cobro_portal', stdout=salida)
        self.assertEqual(sincronizar.call_count, 2)
        self.assertEqual(sincronizar.call_args.kwargs['hoy'], date(2026, 11, 22))
        self.assertIn('clientes=2', salida.getvalue())

    @patch('portal_clientes.management.commands.generar_avisos_cobro_portal.AccesoCliente')
    @patch('portal_clientes.management.commands.generar_avisos_cobro_portal._sincronizar_cobros', side_effect=RuntimeError('fallo simulado'))
    def test_error_detiene_ejecucion(self, sincronizar, acceso):
        acceso.objects.filter.return_value.values_list.return_value.distinct.return_value.iterator.return_value = [11]
        with self.assertRaises(CommandError):
            call_command('generar_avisos_cobro_portal', stdout=StringIO())
