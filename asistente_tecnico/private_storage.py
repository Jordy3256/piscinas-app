"""Almacenamiento privado AQUO360, fuera de MEDIA_ROOT público.
En producción configurar AQUO360_PRIVATE_MEDIA_ROOT en un volumen persistente.
"""
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.utils.deconstruct import deconstructible


@deconstructible
class PrivateAquoStorage(FileSystemStorage):
    def __init__(self):
        import os
        location = os.environ.get("AQUO360_PRIVATE_MEDIA_ROOT") or str(settings.BASE_DIR / "private_aquo360")
        super().__init__(location=location, base_url=None)


private_aquo_storage = PrivateAquoStorage()
