from django.db import models
from mantenimientos.models import Mantenimiento


class ChecklistItem(models.Model):

    mantenimiento = models.ForeignKey(
        Mantenimiento,
        on_delete=models.CASCADE,
        related_name='checklist'
    )
    descripcion = models.CharField(max_length=200)
    realizado = models.BooleanField(default=False)
    observaciones = models.TextField(blank=True)

    def __str__(self):
        return self.descripcion

    class Meta:
        verbose_name = "Ítem de Checklist"
        verbose_name_plural = "Checklist de Mantenimiento"
from contratos.models import Contrato


class ChecklistPlantilla(models.Model):

    contrato = models.ForeignKey(
        Contrato,
        on_delete=models.CASCADE,
        related_name='plantillas_checklist'
    )
    descripcion = models.CharField(max_length=200)

    def __str__(self):
        return f"{self.contrato} - {self.descripcion}"

    class Meta:
        verbose_name = "Plantilla de Checklist"
        verbose_name_plural = "Plantillas de Checklist"
