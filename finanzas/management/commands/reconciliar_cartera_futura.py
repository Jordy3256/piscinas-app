from django.core.management.base import BaseCommand
from django.utils import timezone

from contratos.models import Contrato
from finanzas.sincronizacion import sincronizar_contrato_activo


class Command(BaseCommand):
    help = "Reaplica la configuración vigente de contratos únicamente a Cartera actual/futura no pagada."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Aplica la reconciliación. Sin esta opción solo informa cuántos contratos serían revisados.",
        )
        parser.add_argument("--horizonte", type=int, default=12)

    def handle(self, *args, **options):
        hoy = timezone.localdate()
        contratos = Contrato.objects.filter(activo=True).order_by("id")
        total = contratos.count()
        self.stdout.write(f"Fecha de corte: {hoy:%d/%m/%Y}")
        self.stdout.write(f"Contratos activos a revisar: {total}")
        self.stdout.write("El histórico anterior a la fecha de corte y las cuentas con pagos quedan protegidos.")

        if not options["apply"]:
            self.stdout.write(self.style.WARNING("MODO SEGURO: no se modificó ningún registro."))
            self.stdout.write("Para aplicar: python manage.py reconciliar_cartera_futura --apply")
            return

        totales = {"actualizadas": 0, "creadas": 0, "errores": 0}
        for contrato in contratos.iterator():
            try:
                resultado = sincronizar_contrato_activo(
                    contrato,
                    desde_fecha=hoy,
                    horizonte_meses=max(options["horizonte"], 0),
                )
                totales["actualizadas"] += int(resultado.get("facturas_actualizadas", 0) or 0)
                totales["creadas"] += int(resultado.get("facturas_creadas", 0) or 0)
            except Exception as exc:
                totales["errores"] += 1
                self.stderr.write(self.style.ERROR(f"Contrato {contrato.pk}: {exc}"))

        self.stdout.write(self.style.SUCCESS(
            f"Reconciliación terminada: {totales['actualizadas']} actualizadas, "
            f"{totales['creadas']} creadas, {totales['errores']} errores."
        ))
