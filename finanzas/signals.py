from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from contratos.models import Contrato
from .sincronizacion import sincronizar_contrato_desactivado


@receiver(post_save, sender=Contrato, dispatch_uid="finanzas_sincronizar_contrato_desactivado")
def contrato_guardado_sincronizar_finanzas(sender, instance, **kwargs):
    if not instance.activo:
        transaction.on_commit(lambda: sincronizar_contrato_desactivado(instance))
