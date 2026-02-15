from django.db import models
from clientes.models import Cliente
from contratos.models import Contrato
from trabajadores.models import Trabajador
from inventario.models import Insumo


class Mantenimiento(models.Model):

    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('realizado', 'Realizado'),
    ]

    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    contrato = models.ForeignKey(Contrato, on_delete=models.CASCADE)
    fecha = models.DateField()
    trabajadores = models.ManyToManyField(Trabajador)
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='pendiente'
    )
    observaciones = models.TextField(blank=True)

    def total_egresos(self):
        total = 0
        for uso in self.usos_insumos.all():
            total += uso.subtotal()
        return total

    total_egresos.short_description = "Total egresos"

    def __str__(self):
        return f"{self.cliente} - {self.fecha}"

    class Meta:
        verbose_name = "Mantenimiento"
        verbose_name_plural = "Mantenimientos"


class UsoInsumo(models.Model):
    mantenimiento = models.ForeignKey(
        'mantenimientos.Mantenimiento',
        on_delete=models.CASCADE,
        related_name='usos_insumos'
    )
    insumo = models.ForeignKey(Insumo, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField()

    egreso = models.OneToOneField(
    'finanzas.Egreso',
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name='uso_insumo'
)

    def subtotal(self):
        return self.insumo.precio * self.cantidad

    def __str__(self):
        return f"{self.insumo.nombre} - {self.cantidad}"

class FotoMantenimiento(models.Model):
    mantenimiento = models.ForeignKey(
        'mantenimientos.Mantenimiento',
        on_delete=models.CASCADE,
        related_name='fotos'
    )
    imagen = models.ImageField(upload_to='mantenimientos/')
    descripcion = models.CharField(max_length=200, blank=True)
    creada_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Foto #{self.id} - {self.mantenimiento}"
