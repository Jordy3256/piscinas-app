from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from finanzas.models import Egreso, Ingreso, MovimientoRecurrente
from dashboard.models import Notificacion


class Command(BaseCommand):
    help = "Audita y, con --apply, elimina SOLO movimientos falsos creados por el recurrente histórico en la fecha del incidente."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Aplica la limpieza. Sin esta opción solo muestra candidatos.")
        parser.add_argument("--fecha-incidente", default="2026-09-23", help="Fecha local en que se ejecutó accidentalmente el recurrente histórico (YYYY-MM-DD).")

    def handle(self, *args, **options):
        try:
            fecha_incidente = date.fromisoformat(options["fecha_incidente"])
        except ValueError as exc:
            raise CommandError("--fecha-incidente debe usar YYYY-MM-DD") from exc

        legacy = list(MovimientoRecurrente.objects.filter(es_gasto_manual_recurrente=False))
        ingresos_ids = set()
        egresos_ids = set()

        for mov in legacy:
            monto = Decimal(mov.monto)
            # El código antiguo generaba movimientos sin cliente/contrato y sin trazabilidad.
            if mov.tipo == "ingreso":
                qs = Ingreso.objects.filter(
                    concepto=mov.concepto,
                    total=monto,
                    cliente__isnull=True,
                    contrato__isnull=True,
                    creado_en__date=fecha_incidente,
                )
                ingresos_ids.update(qs.values_list("id", flat=True))
            elif mov.tipo == "egreso":
                qs = Egreso.objects.filter(
                    concepto=mov.concepto,
                    total=monto,
                    mantenimiento__isnull=True,
                    insumo__isnull=True,
                    recurrente__isnull=True,
                    creado_en__date=fecha_incidente,
                )
                egresos_ids.update(qs.values_list("id", flat=True))

        notif_qs = Notificacion.objects.filter(
            creada_en__date=fecha_incidente,
            titulo__in=["💰 Ingreso recurrente generado", "💸 Egreso recurrente generado"],
        )

        self.stdout.write(f"Fecha del incidente: {fecha_incidente}")
        self.stdout.write(f"Recurrentes históricos aislados: {len(legacy)}")
        self.stdout.write(f"Ingresos falsos candidatos: {len(ingresos_ids)}")
        self.stdout.write(f"Egresos falsos candidatos: {len(egresos_ids)}")
        self.stdout.write(f"Notificaciones falsas candidatas: {notif_qs.count()}")

        for obj in Ingreso.objects.filter(id__in=ingresos_ids).order_by("fecha", "id")[:50]:
            self.stdout.write(f"  INGRESO #{obj.id}: {obj.fecha} | {obj.concepto} | ${obj.total}")
        for obj in Egreso.objects.filter(id__in=egresos_ids).order_by("fecha", "id")[:50]:
            self.stdout.write(f"  EGRESO #{obj.id}: {obj.fecha} | {obj.concepto} | ${obj.total}")

        if not options["apply"]:
            self.stdout.write(self.style.WARNING("MODO SEGURO: no se modificó ningún registro."))
            self.stdout.write("Para aplicar exactamente estos candidatos: python manage.py limpiar_recurrentes_legacy --apply")
            return

        with transaction.atomic():
            n_ing, _ = Ingreso.objects.filter(id__in=ingresos_ids).delete()
            n_egr, _ = Egreso.objects.filter(id__in=egresos_ids).delete()
            n_notif, _ = notif_qs.delete()
            MovimientoRecurrente.objects.filter(es_gasto_manual_recurrente=False).update(activo=False)

        self.stdout.write(self.style.SUCCESS(
            f"Limpieza aplicada: {n_ing} ingresos, {n_egr} egresos y {n_notif} notificaciones eliminadas."
        ))
