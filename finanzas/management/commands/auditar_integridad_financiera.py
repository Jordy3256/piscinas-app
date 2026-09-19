from django.core.management.base import BaseCommand
from finanzas.integridad_financiera import auditar_integridad_facturas


class Command(BaseCommand):
    help = 'Audita, en solo lectura, periodos cuyo esquema o importe no coincide con el contrato.'

    def handle(self, *args, **options):
        self.stdout.write('=== AUDITORIA DE INTEGRIDAD FINANCIERA / SOLO LECTURA ===')
        incidencias = auditar_integridad_facturas()
        for x in incidencias:
            self.stdout.write(
                f"CONTRATO {x['contrato_id']} | {x['cliente']} | {x['periodo']} | "
                f"FACTURAS {x['facturas']} | {'; '.join(x['motivos'])}"
            )
        self.stdout.write(f'\nIncidencias detectadas: {len(incidencias)}')
        self.stdout.write('No se modifico ningun registro.')
