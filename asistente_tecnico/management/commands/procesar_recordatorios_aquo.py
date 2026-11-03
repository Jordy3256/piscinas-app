from django.core.management.base import BaseCommand
from asistente_tecnico.notificaciones_automaticas import generar_recordatorios_digitales, enviar_push_digitales


class Command(BaseCommand):
    help = "Genera recordatorios y envía push exclusivamente a suscriptores AQUO360 (cron diario)"

    def handle(self, *args, **options):
        result = generar_recordatorios_digitales()
        self.stdout.write(f"Avisos internos: {result}")
        push = enviar_push_digitales()
        self.stdout.write(self.style.SUCCESS(f"Push AQUO360: {push}"))
