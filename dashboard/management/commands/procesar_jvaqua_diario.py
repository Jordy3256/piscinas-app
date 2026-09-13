import json

from django.core.management.base import BaseCommand, CommandError

from dashboard.proceso_diario import ejecutar_proceso_diario_jvaqua


class Command(BaseCommand):
    help = "Ejecuta el proceso diario automático de JVAQUA ERP."

    def add_arguments(self, parser):
        parser.add_argument(
            "--sin-push",
            action="store_true",
            help="Sincroniza alertas sin enviar notificaciones push.",
        )

    def handle(self, *args, **options):
        resultado = ejecutar_proceso_diario_jvaqua(
            enviar_push=not options["sin_push"],
        )
        self.stdout.write(json.dumps(resultado, ensure_ascii=False, default=str, indent=2))

        if resultado.get("errores"):
            raise CommandError(
                f"Proceso diario finalizó con {len(resultado['errores'])} incidencia(s). "
                "Revisa el detalle anterior."
            )

        self.stdout.write(self.style.SUCCESS("Proceso Diario JVAQUA completado correctamente."))
