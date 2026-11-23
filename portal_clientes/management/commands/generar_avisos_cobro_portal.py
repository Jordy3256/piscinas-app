"""Genera avisos internos de cobro usando la fecha de Ecuador.

Render Cron Job: 0 13 * * * (08:00 America/Guayaquil).
"""
import logging
import os
from zoneinfo import ZoneInfo

from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.utils import timezone

from portal_clientes.models import AccesoCliente
from portal_clientes.notificaciones import _sincronizar_cobros

logger = logging.getLogger(__name__)
ECUADOR = ZoneInfo('America/Guayaquil')


class Command(BaseCommand):
    help = 'Sincroniza avisos de cobro del portal sin enviar mensajes externos.'

    def handle(self, *args, **options):
        # En Render nunca permitir una ejecución accidental sobre SQLite local.
        if os.environ.get('RENDER') and connection.vendor != 'postgresql':
            raise CommandError('Render Cron debe usar PostgreSQL: comprueba DATABASE_URL.')

        with timezone.override(ECUADOR):
            hoy = timezone.localdate()
            clientes = (AccesoCliente.objects.filter(
                habilitado=True, usuario__isnull=False, cliente__activo=True
            ).values_list('cliente_id', flat=True).distinct().iterator(chunk_size=200))
            revisados = 0
            candidatos = 0
            for cliente_id in clientes:
                try:
                    candidatos += _sincronizar_cobros(cliente_id, hoy=hoy)
                except Exception as exc:
                    logger.exception('Error al generar avisos del cliente id=%s', cliente_id)
                    raise CommandError('La sincronización se interrumpió; revisa los logs.') from exc
                revisados += 1

            self.stdout.write(self.style.SUCCESS(
                f'Avisos JVAQUA | fecha Ecuador={hoy} | clientes={revisados} '
                f'| avisos candidatos={candidatos} (duplicados ignorados) | resultado=OK'
            ))
