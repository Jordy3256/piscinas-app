"""Resumen push financiero diario (programar 10:00 Ecuador / 15:00 UTC)."""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from dashboard.models import Notificacion
from finanzas.alertas_financieras import generar_alertas_financieras, _usuarios_admin
from finanzas.models import Factura


class Command(BaseCommand):
    help = "Envía un solo resumen financiero push por administrador y día (Ecuador)."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Calcula el resumen sin enviarlo")

    def handle(self, *args, **options):
        # Las alertas individuales se mantienen dentro de la aplicación.
        generar_alertas_financieras(enviar_push=False)
        hoy = timezone.localdate()
        facturas = Factura.objects.exclude(estado=Factura.ESTADO_ANULADA).select_related('cliente')
        vencidos = hoy_cobros = facturas_pendientes = 0
        saldo_vencido = saldo_hoy = 0
        for factura in facturas.iterator():
            if factura.saldo > 0:
                if factura.fecha_vencimiento < hoy:
                    vencidos += 1
                    saldo_vencido += factura.saldo
                elif (factura.fecha_cobro_desde or factura.fecha_vencimiento) <= hoy <= factura.fecha_vencimiento:
                    hoy_cobros += 1
                    saldo_hoy += factura.saldo
            if (factura.requiere_factura and not factura.factura_enviada
                    and factura.fecha_facturacion_programada
                    and factura.fecha_facturacion_programada <= hoy):
                facturas_pendientes += 1
        titulo = '💰 AQUO 360 · Resumen financiero'
        mensaje = (f'🔴 {vencidos} cobros vencidos (${saldo_vencido:.2f}) · '
                   f'🟠 {hoy_cobros} por cobrar (${saldo_hoy:.2f}) · '
                   f'🧾 {facturas_pendientes} facturas pendientes.')
        self.stdout.write(f'{hoy}: {mensaje}')
        if options['dry_run']:
            return
        from dashboard.views import _send_push_to_user
        for usuario in _usuarios_admin():
            # Registro único en PostgreSQL para evitar push repetidos al reejecutar el cron.
            # El envío solo se intenta cuando se crea el registro diario.
            with transaction.atomic():
                _, creado = Notificacion.objects.get_or_create(
                    user=usuario,
                    tipo='resumen_financiero_diario',
                    referencia_id=hoy.toordinal(),
                    defaults={'titulo': titulo, 'mensaje': mensaje,
                              'url': '/dashboard/finanzas/'},
                )
            if not creado:
                self.stdout.write(f'Ya enviado/registrado hoy: {usuario.pk}')
                continue
            try:
                resultado = _send_push_to_user(
                    usuario, titulo, mensaje,
                    url='/dashboard/finanzas/',
                    tag=f'resumen-financiero-{hoy.isoformat()}',
                )
                self.stdout.write(f'Administrador {usuario.pk}: {resultado}')
            except Exception as exc:
                self.stderr.write(f'No se pudo enviar a {usuario.pk}: {exc}')
