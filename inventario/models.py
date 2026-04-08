from django.db import models

class Insumo(models.Model):
    nombre = models.CharField(max_length=100)
    stock = models.PositiveIntegerField(default=0)
    stock_minimo = models.PositiveIntegerField(default=5)
    precio = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return self.nombre

    @property
    def bajo_stock(self):
        return self.stock <= self.stock_minimo

class VentaInsumo(models.Model):
    insumo = models.ForeignKey("Insumo", on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    fecha = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.insumo.nombre} x{self.cantidad} - ${self.total}"