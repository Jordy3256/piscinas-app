from django.db import models
from inventario.models import Insumo
from clientes.models import Cliente
from contratos.models import Contrato


# =====================================================
# EGRESOS (ya lo tenías, no se modifica la lógica)
# =====================================================
class Egreso(models.Model):
    mantenimiento = models.ForeignKey(
        'mantenimientos.Mantenimiento',
        on_delete=models.CASCADE,
        related_name='egresos'
    )
    insumo = models.ForeignKey(Insumo, on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField()
    costo_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    fecha = models.DateField(auto_now_add=True)

    def save(self, *args, **kwargs):
        self.total = self.cantidad * self.costo_unitario
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.insumo.nombre} - {self.total}"

    class Meta:
        verbose_name = "Egreso"
        verbose_name_plural = "Egresos"


# =====================================================
# INGRESOS
# =====================================================
class Ingreso(models.Model):
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )
    contrato = models.ForeignKey(
        Contrato,
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )

    concepto = models.CharField(max_length=120)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    fecha = models.DateField()

    def __str__(self):
        return f"{self.fecha} - {self.concepto} - {self.total}"

    class Meta:
        verbose_name = "Ingreso"
        verbose_name_plural = "Ingresos"


# =====================================================
# MOVIMIENTOS RECURRENTES (gastos fijos / ingresos fijos)
# =====================================================
class MovimientoRecurrente(models.Model):
    TIPO_CHOICES = [
        ("ingreso", "Ingreso"),
        ("egreso", "Egreso"),
    ]

    FRECUENCIA_CHOICES = [
        ("mensual", "Mensual"),
        ("semanal", "Semanal"),
    ]

    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    concepto = models.CharField(max_length=120)
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    frecuencia = models.CharField(
        max_length=10,
        choices=FRECUENCIA_CHOICES,
        default="mensual"
    )
    proxima_fecha = models.DateField()
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.tipo.upper()} - {self.concepto} - {self.monto}"

    class Meta:
        verbose_name = "Movimiento recurrente"
        verbose_name_plural = "Movimientos recurrentes"
