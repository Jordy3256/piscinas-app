from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from contratos.models import Contrato
from trabajadores.models import Trabajador
from .sincronizacion import (
    sincronizar_contrato_activo,
    sincronizar_contrato_desactivado,
    sincronizar_modalidad_remuneracion_trabajador,
)


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



@receiver(post_save, sender=Trabajador, dispatch_uid="finanzas_sincronizar_modalidad_trabajador")
def trabajador_guardado_sincronizar_nomina(sender, instance, **kwargs):
    """Mantiene la nómina alineada con la modalidad de remuneración elegida."""
    transaction.on_commit(
        lambda: sincronizar_modalidad_remuneracion_trabajador(instance)
    )
