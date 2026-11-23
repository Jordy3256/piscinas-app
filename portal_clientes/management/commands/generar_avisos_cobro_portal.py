"""Genera avisos internos de cobro del portal para el día de Ecuador.

Ejecutar una vez al día desde el programador de Render o equivalente:
    python manage.py generar_avisos_cobro_portal
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from portal_clientes.models import AccesoCliente
from portal_clientes.notificaciones import _sincronizar_cobros


class Command(BaseCommand):
    help = 'Sincroniza avisos de cobro del portal sin enviar mensajes externos.'

    def handle(self, *args, **options):
        hoy = timezone.localdate()
        clientes = (AccesoCliente.objects.filter(habilitado=True, usuario__isnull=False,
                                                  cliente__activo=True)
                    .values_list('cliente_id', flat=True).iterator(chunk_size=200))
        total = 0
        revisados = 0
        for cliente_id in clientes:
            total += _sincronizar_cobros(cliente_id, hoy=hoy)
            revisados += 1
        self.stdout.write(self.style.SUCCESS(
            f'Sincronización {hoy}: {revisados} clientes revisados; hasta {total} avisos candidatos (duplicados ignorados).'
        ))
