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
    insumo = models.ForeignKey("Insumo", on_delete=models.CASCADE, related_name="ventas")
    cantidad = models.PositiveIntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    fecha = models.DateField(auto_now_add=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.insumo.nombre} x{self.cantidad} - ${self.total}"

class Meta:
    verbose_name = "Venta de insumo"
    verbose_name_plural = "Ventas de insumos"
    ordering = ["-fecha", "-id"]

class EntradaStock(models.Model):
    insumo = models.ForeignKey("Insumo", on_delete=models.CASCADE, related_name="entradas_stock")
    cantidad = models.PositiveIntegerField()
    observacion = models.CharField(max_length=255, blank=True)
    fecha = models.DateField(auto_now_add=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Entrada {self.insumo.nombre} x{self.cantidad}"

class Meta:
    verbose_name = "Entrada de stock"
    verbose_name_plural = "Entradas de stock"
    ordering = ["-fecha", "-id"]

class MovimientoInventario(models.Model):
    TIPO_CHOICES = [
    ("entrada", "Entrada"),
    ("venta", "Venta"),
    ("mantenimiento", "Mantenimiento"),
    ("ajuste", "Ajuste"),
    ]

    insumo = models.ForeignKey("Insumo", on_delete=models.CASCADE, related_name="movimientos")
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    cantidad = models.PositiveIntegerField()
    stock_anterior = models.PositiveIntegerField(default=0)
    stock_resultante = models.PositiveIntegerField(default=0)
    observacion = models.CharField(max_length=255, blank=True)
    fecha = models.DateField(auto_now_add=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.insumo.nombre} x{self.cantidad}"

class Meta:
    verbose_name = "Movimiento de inventario"
    verbose_name_plural = "Movimientos de inventario"
    ordering = ["-fecha", "-id"]