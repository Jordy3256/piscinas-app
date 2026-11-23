"""Regresión Fase 9C: comandos históricos sin efectos laterales."""
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import SimpleTestCase


class ComandosDigitalesRetiradosTests(SimpleTestCase):
    def test_recordatorios_aquo_no_importan_servicios_ni_usan_bd(self):
        salida = StringIO()
        with patch("asistente_tecnico.notificaciones_automaticas.generar_recordatorios_digitales", side_effect=AssertionError("No debe ejecutarse")), patch("asistente_tecnico.notificaciones_automaticas.enviar_push_digitales", side_effect=AssertionError("No debe ejecutarse")):
            call_command("procesar_recordatorios_aquo", stdout=salida)
        self.assertIn("no se generaron recordatorios", salida.getvalue())

    def test_cobros_aquo_no_importan_servicios_ni_usan_bd(self):
        salida = StringIO()
        with patch("asistente_tecnico.cartera_digital.crear_cobros_mes", side_effect=AssertionError("No debe ejecutarse")), patch("asistente_tecnico.cartera_digital.generar_avisos_cobros", side_effect=AssertionError("No debe ejecutarse")):
            call_command("generar_recordatorios_cobros_aquo", stdout=salida)
        self.assertIn("no se generaron cargos", salida.getvalue())
