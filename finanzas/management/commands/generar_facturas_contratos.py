from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from finanzas.cuentas_por_cobrar import generar_facturas_periodo


class Command(BaseCommand):
    help = "Genera las cuentas por cobrar mensuales de todos los contratos activos."

    def add_arguments(self, parser):
        hoy = timezone.localdate()
        parser.add_argument("--anio", type=int, default=hoy.year)
        parser.add_argument("--mes", type=int, default=hoy.month)

    def handle(self, *args, **options):
        anio, mes = options["anio"], options["mes"]
        if not 1 <= mes <= 12:
            raise CommandError("El mes debe estar entre 1 y 12.")
        resultado = generar_facturas_periodo(anio, mes)
        self.stdout.write(self.style.SUCCESS(
            f"Periodo {mes:02d}/{anio}: {resultado['creadas']} creadas, "
            f"{resultado['existentes']} ya existentes."
        ))
        for error in resultado["errores"]:
            self.stderr.write(error)
