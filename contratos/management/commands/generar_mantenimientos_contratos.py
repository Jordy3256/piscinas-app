from django.core.management.base import BaseCommand
from contratos.programacion import mantener_programacion_automatica


class Command(BaseCommand):
    help = "Verifica y completa las visitas futuras de todos los contratos activos sin duplicarlas."

    def add_arguments(self, parser):
        parser.add_argument("--dias", type=int, default=60, help="Horizonte de programación (por defecto 60 días).")

    def handle(self, *args, **options):
        dias = options["dias"]
        if not 1 <= dias <= 365:
            raise ValueError("--dias debe estar entre 1 y 365")
        resultado = mantener_programacion_automatica(horizonte_dias=dias)
        self.stdout.write(self.style.SUCCESS(
            f"Contratos revisados: {resultado['renovados']}; "
            f"visitas creadas: {resultado['creados']}; "
            f"existentes: {resultado['existentes']}; "
            f"contratos con error: {len(resultado['errores'])}."
        ))
        for error in resultado["errores"]:
            self.stderr.write(f"Contrato #{error['contrato']}: {error['errores']}")
