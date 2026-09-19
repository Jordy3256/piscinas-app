from collections import defaultdict
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from finanzas.models import Factura


class Command(BaseCommand):
    help = (
        "Audita periodos de cartera con esquemas de cuotas incompatibles (p. ej. 1/1 + 2/2). "
        "Por defecto es solo lectura. --apply solo anula facturas sospechosas SIN pagos activos."
    )

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Aplica anulacion conservadora solo a candidatas sin pagos activos.")
        parser.add_argument("--invoice-ids", nargs="+", type=int, help="Limita --apply a IDs aprobados explicitamente.")

    def handle(self, *args, **options):
        aplicar = options["apply"]
        ids = set(options.get("invoice_ids") or [])
        if aplicar and not ids:
            raise CommandError("Por seguridad, --apply requiere --invoice-ids con IDs revisados y aprobados.")

        qs = (
            Factura.objects.select_related("cliente", "contrato")
            .prefetch_related("pagos")
            .exclude(estado=Factura.ESTADO_ANULADA)
            .order_by("contrato_id", "periodo_anio", "periodo_mes", "creada_en", "id")
        )
        grupos = defaultdict(list)
        for f in qs:
            grupos[(f.contrato_id, f.periodo_anio, f.periodo_mes)].append(f)

        candidatas = []
        manuales = []
        grupos_conflictivos = 0
        self.stdout.write("=== AUDITORIA CONSERVADORA DE CARTERA ===")
        self.stdout.write("Modo: %s" % ("APLICAR" if aplicar else "DRY-RUN / SOLO LECTURA"))

        for clave, facturas in grupos.items():
            esquemas = {int(f.total_cuotas or 1) for f in facturas}
            if len(esquemas) <= 1:
                continue

            # Solo clasificamos automaticamente el patron probado: un periodo ya materializado
            # como cuota unica 1/1 y luego complementado con cuotas de un esquema fraccionado.
            completas = [f for f in facturas if int(f.cuota_numero or 1) == 1 and int(f.total_cuotas or 1) == 1]
            if not completas:
                continue
            base = min(completas, key=lambda f: (f.creada_en, f.id))
            sospechosas = [
                f for f in facturas
                if int(f.total_cuotas or 1) > 1 and (f.creada_en, f.id) > (base.creada_en, base.id)
            ]
            if not sospechosas:
                continue

            grupos_conflictivos += 1
            self.stdout.write("")
            self.stdout.write(
                f"CONTRATO {base.contrato_id} | CLIENTE {base.cliente} | "
                f"PERIODO {base.periodo_anio}-{base.periodo_mes:02d}"
            )
            self.stdout.write(
                f"  BASE #{base.id} | {base.cuota_numero}/{base.total_cuotas} | "
                f"TOTAL ${base.total} | ESTADO {base.estado} | CREADA {base.creada_en}"
            )

            for f in sospechosas:
                pagos = [p for p in f.pagos.all() if p.activo]
                pagado = sum((p.monto for p in pagos), Decimal("0.00"))
                if pagos:
                    manuales.append(f.id)
                    accion = "REVISION MANUAL: TIENE PAGO ACTIVO"
                else:
                    candidatas.append(f.id)
                    accion = "CANDIDATA A ANULAR (SIN PAGOS)"
                self.stdout.write(
                    f"  SOSPECHOSA #{f.id} | {f.cuota_numero}/{f.total_cuotas} | "
                    f"TOTAL ${f.total} | ESTADO {f.estado} | PAGADO ${pagado} | "
                    f"CREADA {f.creada_en} | {accion}"
                )

        self.stdout.write("")
        self.stdout.write("=== RESUMEN ===")
        self.stdout.write(f"Grupos conflictivos detectados: {grupos_conflictivos}")
        self.stdout.write(f"Candidatas sin pagos: {len(candidatas)} -> {candidatas}")
        self.stdout.write(f"Con pagos / revision manual: {len(manuales)} -> {manuales}")

        if not aplicar:
            self.stdout.write(self.style.WARNING("DRY-RUN: no se modifico ningun registro."))
            return

        no_candidatas = sorted(ids - set(candidatas))
        if no_candidatas:
            raise CommandError(
                "Estos IDs no son candidatas seguras sin pagos segun la auditoria actual: " + str(no_candidatas)
            )

        with transaction.atomic():
            bloqueadas = []
            anuladas = []
            for factura in Factura.objects.select_for_update().filter(id__in=sorted(ids)):
                if factura.pagos.filter(activo=True).exists():
                    bloqueadas.append(factura.id)
                    continue
                marca = "[SANEAMIENTO CARTERA] Anulada por conflicto historico de esquema de cuotas (periodo previamente materializado con esquema distinto)."
                factura.estado = Factura.ESTADO_ANULADA
                factura.pagada_en = None
                factura.observaciones = (factura.observaciones.rstrip() + "\n" + marca).strip()
                factura.save(update_fields=["estado", "pagada_en", "observaciones", "actualizada_en"])
                anuladas.append(factura.id)
            if bloqueadas:
                raise CommandError("Se detectaron pagos activos durante la transaccion; no se aplico ningun cambio: " + str(bloqueadas))

        self.stdout.write(self.style.SUCCESS(f"Facturas anuladas de forma conservadora: {anuladas}"))
