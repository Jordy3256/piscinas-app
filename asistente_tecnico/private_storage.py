"""Archivos privados exclusivos de AQUO360; nunca ofrecer URLs públicas.

En Render: AQUO360_PRIVATE_MEDIA_ROOT=/var/data/aquo360
El disco debe estar montado en /var/data antes de recibir archivos.
"""
import os
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.utils.deconstruct import deconstructible


@deconstructible
class PrivateAquoStorage(FileSystemStorage):
    def __init__(self):
        location = os.environ.get("AQUO360_PRIVATE_MEDIA_ROOT") or str(settings.BASE_DIR / "private_aquo360")
        super().__init__(location=location, base_url=None)

    def url(self, name):
        # FileSystemStorage puede usar MEDIA_URL aun con base_url=None.
        # Estos documentos solo se entregan mediante vistas con permisos.
        raise ValueError("Los archivos privados AQUO360 no tienen URL pública")


private_aquo_storage = PrivateAquoStorage()
