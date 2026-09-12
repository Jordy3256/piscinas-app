from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from contratos.models import Contrato
from .sincronizacion import sincronizar_contrato_activo, sincronizar_contrato_desactivado


@receiver(post_save, sender=Contrato, dispatch_uid="finanzas_sincronizar_contrato_desactivado")
def contrato_guardado_sincronizar_finanzas(sender, instance, created=False, **kwargs):
    """
    Cartera y Nómina siguen al contrato automáticamente.

    - Nuevo: materializa desde la fecha de inicio.
    - Edición: mantiene desde el periodo actual hacia adelante.
    - Baja: retira pendientes no devengados/futuros.
    """
    if not instance.activo:
        transaction.on_commit(
            lambda: sincronizar_contrato_desactivado(instance)
        )
        return

    desde = instance.fecha_inicio if created else None
    transaction.on_commit(
        lambda: sincronizar_contrato_activo(
            instance,
            desde_fecha=desde,
            horizonte_meses=12,
        )
    )
