from django.db import models
from clientes.models import Cliente


class Contrato(models.Model):

    FRECUENCIA_CHOICES = [
        ('semanal', 'Semanal'),
        ('quincenal', 'Quincenal'),
        ('mensual', 'Mensual'),
        ('variable', 'Variable'),
    ]

    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    tipo = models.CharField(max_length=20, choices=FRECUENCIA_CHOICES)
    precio_mensual = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_inicio = models.DateField()
    activo = models.BooleanField(default=True)

    def ingreso_mensual(self):
        return self.precio_mensual

    def __str__(self):
        return f"{self.cliente.nombre} - {self.tipo}"