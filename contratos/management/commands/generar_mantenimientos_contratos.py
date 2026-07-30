from django.core.management.base import BaseCommand
from django.utils import timezone

from contratos.models import Contrato
from contratos.programacion import generar_mantenimientos_contrato, sumar_un_mes


class Command(BaseCommand):
    help = "Mantiene un mes de visitas futuras generado para todos los contratos activos."

    def handle(self, *args, **options):
        hoy = timezone.localdate()
        horizonte = sumar_un_mes(hoy)
        contratos = Contrato.objects.filter(
            activo=True,
            generacion_automatica=True,
            tecnico_designado__isnull=False,
        ).select_related("cliente", "tecnico_designado")

        total_creados = 0
        total_existentes = 0
        con_error = 0

        for contrato in contratos.iterator():
            resultado = generar_mantenimientos_contrato(
                contrato,
                desde=max(hoy, contrato.fecha_inicio),
                hasta=horizonte,
                reconciliar=False,
            )
            if resultado.get("errores"):
                con_error += 1
                self.stderr.write(
                    f"Contrato #{contrato.pk}: {'; '.join(resultado['errores'])}"
                )
                continue
            total_creados += resultado["creados"]
            total_existentes += resultado["existentes"]

        self.stdout.write(
            self.style.SUCCESS(
                f"Programación completada. Nuevos: {total_creados}. "
                f"Ya existentes: {total_existentes}. Con error: {con_error}."
            )
        )
