"""Compatibilidad con cron antiguo de AQUO360; sin efectos en el ERP."""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Retirado: los recordatorios de suscriptores AQUO360 no se ejecutan en JVAQUA."

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING(
            "AQUO360 retirado del ERP JVAQUA: no se generaron recordatorios ni se enviaron notificaciones."
        ))
