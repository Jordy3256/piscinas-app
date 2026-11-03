"""Auditoría de configuración AQUO360, sin modificar registros ni enviar notificaciones."""
import os
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import DatabaseError
from django.utils import timezone

from asistente_tecnico.models import (
    PerfilSuscriptor, SolicitudSuscripcionDigital, SuscripcionPushDigital,
    VisitaProgramadaPiscina,
)


class Command(BaseCommand):
    help = "Comprueba configuración de AQUO360 y contabiliza pendientes sin modificar datos."

    def handle(self, *args, **options):
        self.stdout.write("AUDITORÍA PRELANZAMIENTO AQUO360 (solo lectura)")
        self.stdout.write(f"Fecha local: {timezone.localdate()}")
        self.stdout.write("Separación: solo modelos de asistente_tecnico; sin consultas a tablas del ERP.")
        avisos = []
        if not os.environ.get("AQUO360_PRIVATE_MEDIA_ROOT"):
            avisos.append("No hay AQUO360_PRIVATE_MEDIA_ROOT: las fotos privadas pueden perderse en un disco efímero.")
        else:
            private_root = Path(os.environ["AQUO360_PRIVATE_MEDIA_ROOT"]).expanduser()
            if not private_root.is_absolute():
                avisos.append("AQUO360_PRIVATE_MEDIA_ROOT debe ser una ruta absoluta persistente.")
            elif private_root.resolve().is_relative_to(Path(settings.MEDIA_ROOT).resolve()):
                avisos.append("AQUO360_PRIVATE_MEDIA_ROOT está dentro de MEDIA_ROOT público: corrige la ubicación.")

        if not os.environ.get("VAPID_PRIVATE_KEY") and not getattr(settings, "VAPID_PRIVATE_KEY", ""):
            avisos.append("Falta clave privada VAPID: no se enviarán push.")
        if not os.environ.get("AQUO360_CRON_CONFIGURADO"):
            avisos.append("Confirmar manualmente el cron diario de Render a las 12:10 UTC; este comando no lo configura.")

        cloudinary = bool(os.environ.get("CLOUDINARY_URL"))
        if cloudinary:
            avisos.append("CLOUDINARY_URL habilitado: comprobar y migrar comprobantes antiguos alojados en URLs públicas.")
        else:
            avisos.append("Los comprobantes locales quedan bloqueados por /media/, pero requieren almacenamiento privado persistente antes del lanzamiento.")

        try:
            self.stdout.write(f"Suscriptores digitales: {PerfilSuscriptor.objects.count()}")
            self.stdout.write(f"Solicitudes pendientes: {SolicitudSuscripcionDigital.objects.filter(estado='pendiente').count()}")
            self.stdout.write(f"Visitas digitales hoy: {VisitaProgramadaPiscina.objects.filter(fecha=timezone.localdate()).count()}")
            self.stdout.write(f"Dispositivos push digitales: {SuscripcionPushDigital.objects.count()}")
            self.stdout.write(f"Comprobantes históricos: {SolicitudSuscripcionDigital.objects.exclude(comprobante='').filter(comprobante__isnull=False).count()}")
        except DatabaseError as exc:
            avisos.append(f"No se pudo consultar la base de datos de AQUO360: {type(exc).__name__}")

        if avisos:
            self.stdout.write(self.style.WARNING("Pendientes de verificación:"))
            for aviso in avisos:
                self.stdout.write(f" - {aviso}")
        else:
            self.stdout.write(self.style.SUCCESS("Configuración sin advertencias detectadas."))
        self.stdout.write("No se generaron avisos, no se enviaron push y no se modificaron datos.")
