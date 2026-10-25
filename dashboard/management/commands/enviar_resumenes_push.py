from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from zoneinfo import ZoneInfo
from dashboard.notificaciones_inteligentes import enviar_resumenes


class Command(BaseCommand):
    help = 'Resúmenes de mantenimientos pendientes (08, 14 y 20, Ecuador). Idempotente.'

    def add_arguments(self, parser):
        parser.add_argument('--hora', type=int, choices=(8, 14, 20), help='Hora Ecuador; omitir para detectar automáticamente')
        parser.add_argument('--dry-run', action='store_true', help='No guarda ni envía notificaciones')

    def handle(self, *args, **opts):
        ahora = timezone.localtime(timezone.now(), ZoneInfo('America/Guayaquil'))
        hora = opts['hora'] if opts['hora'] is not None else ahora.hour
        if hora not in (8, 14, 20):
            self.stdout.write('Fuera de horarios de resumen; no se envió nada.')
            return
        if opts['hora'] is None and ahora.minute > 15:
            self.stdout.write('Fuera de ventana de envío (primeros 15 minutos).')
            return
        resultado = enviar_resumenes(hora, dry_run=opts['dry_run'])
        self.stdout.write(self.style.SUCCESS(f'Resúmenes {hora:02d}:00 (dry_run={opts["dry_run"]}): {resultado}'))
