from django.core.management.base import BaseCommand

from finanzas.alertas_financieras import generar_alertas_financieras


class Command(BaseCommand):
    help = (
        "Sincroniza los recordatorios internos de facturación y las demás alertas "
        "financieras usando la lógica central del sistema."
    )

    def handle(self, *args, **options):
        total = generar_alertas_financieras(enviar_push=False)
        self.stdout.write(
            self.style.SUCCESS(
                f"Alertas financieras sincronizadas: {total}. "
                "Las facturas externas permanecen pendientes hasta marcarlas como realizadas."
            )
        )
