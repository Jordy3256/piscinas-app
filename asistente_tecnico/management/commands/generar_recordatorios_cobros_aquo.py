"""Compatibilidad con cron antiguo de cartera AQUO360; sin efectos en el ERP."""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Retirado: los cobros y avisos de suscriptores AQUO360 no se generan en JVAQUA."

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING(
            "AQUO360 retirado del ERP JVAQUA: no se generaron cargos ni avisos de cobro."
        ))
