"""Copiar comprobantes locales previos al almacenamiento privado sin borrar originales.

La opción --apply requiere AQUO360_PRIVATE_MEDIA_ROOT y un respaldo previo.
No pretende migrar archivos alojados en Cloudinary u otro proveedor remoto.
"""
import hashlib
import os
from pathlib import Path, PurePosixPath

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError

from asistente_tecnico.models import SolicitudSuscripcionDigital
from asistente_tecnico.private_storage import private_aquo_storage


def sha256_file(fileobj):
    digest = hashlib.sha256()
    for bloque in iter(lambda: fileobj.read(1024 * 1024), b""):
        digest.update(bloque)
    return digest.hexdigest()


class Command(BaseCommand):
    help = "Vista previa o copia segura de comprobantes AQUO360 antiguos a almacenamiento privado."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Copiar los archivos verificados (sin borrar originales).")

    def handle(self, *args, **options):
        aplicar = options["apply"]
        root = os.environ.get("AQUO360_PRIVATE_MEDIA_ROOT", "").strip()
        if aplicar and not root:
            raise CommandError("Configure AQUO360_PRIVATE_MEDIA_ROOT en un volumen persistente antes de --apply.")
        if aplicar and not Path(root).is_absolute():
            raise CommandError("AQUO360_PRIVATE_MEDIA_ROOT debe ser una ruta absoluta.")

        original_root = Path(settings.MEDIA_ROOT).resolve()
        revisados = listos = faltantes = conflictos = copiados = 0
        for solicitud in SolicitudSuscripcionDigital.objects.exclude(comprobante="").exclude(comprobante__isnull=True).iterator():
            nombre = solicitud.comprobante.name
            ruta = PurePosixPath(nombre)
            if ruta.is_absolute() or ".." in ruta.parts or not nombre.startswith("jvaqua_digital/comprobantes/"):
                continue  # Solo gestionar la estructura heredada conocida.
            revisados += 1
            fuente = (original_root / Path(*ruta.parts)).resolve()
            if not fuente.is_relative_to(original_root) or not fuente.is_file():
                if private_aquo_storage.exists(nombre):
                    listos += 1
                else:
                    faltantes += 1
                    self.stdout.write(self.style.WARNING(f"Sin archivo local: solicitud {solicitud.pk}"))
                continue
            if private_aquo_storage.exists(nombre):
                with fuente.open("rb") as origen, private_aquo_storage.open(nombre, "rb") as destino:
                    mismo = sha256_file(origen) == sha256_file(destino)
                if mismo:
                    listos += 1
                else:
                    conflictos += 1
                    self.stdout.write(self.style.ERROR(f"Conflicto de contenido: solicitud {solicitud.pk}; no sobrescrita"))
                continue
            if aplicar:
                with fuente.open("rb") as origen:
                    nombre_guardado = private_aquo_storage.save(nombre, File(origen))
                if nombre_guardado != nombre:
                    # No dejar que una normalización o colisión cambie el archivo sin reflejarlo en la BD.
                    SolicitudSuscripcionDigital.objects.filter(pk=solicitud.pk).update(comprobante=nombre_guardado)
                with fuente.open("rb") as origen, private_aquo_storage.open(nombre_guardado, "rb") as destino:
                    if sha256_file(origen) != sha256_file(destino):
                        raise CommandError(f"La copia de la solicitud {solicitud.pk} no coincide con el original.")
                copiados += 1
                self.stdout.write(self.style.SUCCESS(f"Copia verificada: solicitud {solicitud.pk}"))
            else:
                self.stdout.write(f"Copiable: solicitud {solicitud.pk}")

        self.stdout.write(
            f"Comprobantes heredados revisados: {revisados}; ya privados: {listos}; "
            f"no localizados: {faltantes}; conflictos: {conflictos}; copiados: {copiados}."
        )
        if not aplicar:
            self.stdout.write("VISTA PREVIA: no se copiaron, borraron ni modificaron archivos o registros.")
        else:
            self.stdout.write("Archivos originales conservados: revisar y retirar por separado cuando sea seguro.")
