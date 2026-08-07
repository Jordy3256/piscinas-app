from decimal import Decimal

from django.contrib.auth.models import User
from django.db import models


Q3 = Decimal("0.001")


class Insumo(models.Model):
    CATEGORIA_CHOICES = [
        ("quimicos", "Químicos"),
        ("repuestos", "Repuestos"),
        ("herramientas", "Herramientas"),
        ("equipos", "Equipos"),
        ("construccion", "Materiales de construcción"),
        ("otros", "Otros"),
    ]
    UNIDAD_CHOICES = [
        ("kg", "Kilogramos"),
        ("unidad", "Unidades"),
    ]

    nombre = models.CharField(max_length=100)
    codigo = models.CharField(max_length=40, blank=True, default="", db_index=True)
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES, default="quimicos", db_index=True)
    unidad_base = models.CharField(max_length=10, choices=UNIDAD_CHOICES, default="kg")
    stock = models.DecimalField(max_digits=12, decimal_places=3, default=Decimal("0.000"))
    stock_minimo = models.DecimalField(max_digits=12, decimal_places=3, default=Decimal("5.000"))
    stock_maximo = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    precio = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"), help_text="Precio de venta por unidad base.")
    costo = models.DecimalField(max_digits=12, decimal_places=4, default=Decimal("0.0000"), help_text="Costo promedio por unidad base.")
    activo = models.BooleanField(default=True, db_index=True)
    puede_venderse = models.BooleanField(default=True)
    puede_mantenimiento = models.BooleanField(default=True)
    puede_asignarse_trabajador = models.BooleanField(default=True)
    puede_construccion = models.BooleanField(default=False)

    def __str__(self):
        return self.nombre

    @property
    def bajo_stock(self):
        return self.stock <= self.stock_minimo

    @property
    def sin_stock(self):
        return self.stock <= 0

    @property
    def utilidad_unitaria(self):
        return self.precio - Decimal(self.costo or 0)

    @property
    def unidad_corta(self):
        return "kg" if self.unidad_base == "kg" else "unid."

    class Meta:
        verbose_name = "Insumo"
        verbose_name_plural = "Insumos"
        ordering = ["nombre"]


class PresentacionInsumo(models.Model):
    insumo = models.ForeignKey(Insumo, on_delete=models.CASCADE, related_name="presentaciones")
    nombre = models.CharField(max_length=80)
    cantidad_base = models.DecimalField(max_digits=12, decimal_places=3, help_text="Cantidad equivalente en la unidad base del producto.")
    precio_venta = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    activa = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.insumo.nombre} · {self.nombre}"

    class Meta:
        verbose_name = "Presentación de insumo"
        verbose_name_plural = "Presentaciones de insumos"
        ordering = ["insumo__nombre", "cantidad_base"]


class InventarioTrabajador(models.Model):
    trabajador = models.ForeignKey("trabajadores.Trabajador", on_delete=models.CASCADE, related_name="inventario_asignado")
    insumo = models.ForeignKey(Insumo, on_delete=models.PROTECT, related_name="stocks_trabajadores")
    stock = models.DecimalField(max_digits=12, decimal_places=3, default=Decimal("0.000"))
    actualizado_en = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.trabajador} · {self.insumo}: {self.stock} {self.insumo.unidad_corta}"

    class Meta:
        verbose_name = "Inventario de trabajador"
        verbose_name_plural = "Inventarios de trabajadores"
        constraints = [
            models.UniqueConstraint(fields=["trabajador", "insumo"], name="uniq_inventario_trabajador_insumo")
        ]
        ordering = ["trabajador__user__username", "insumo__nombre"]


class VentaInsumo(models.Model):
    insumo = models.ForeignKey(Insumo, on_delete=models.PROTECT, related_name="ventas")
    cantidad = models.DecimalField(max_digits=12, decimal_places=3)
    unidad_registro = models.CharField(max_length=15, default="base")
    presentacion = models.ForeignKey(PresentacionInsumo, on_delete=models.SET_NULL, null=True, blank=True, related_name="ventas")
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    costo_unitario = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    ganancia = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    fecha = models.DateField(auto_now_add=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.insumo.nombre} {self.cantidad} {self.insumo.unidad_corta} - ${self.total}"

    class Meta:
        verbose_name = "Venta de insumo"
        verbose_name_plural = "Ventas de insumos"
        ordering = ["-fecha", "-id"]


class CompraInsumo(models.Model):
    insumo = models.ForeignKey(Insumo, on_delete=models.PROTECT, related_name="compras")
    cantidad = models.DecimalField(max_digits=12, decimal_places=3)
    costo_unitario = models.DecimalField(max_digits=12, decimal_places=4)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    proveedor = models.CharField(max_length=150, blank=True, default="")
    observacion = models.CharField(max_length=255, blank=True, default="")
    fecha = models.DateField(auto_now_add=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    egreso = models.OneToOneField("finanzas.Egreso", on_delete=models.SET_NULL, null=True, blank=True, related_name="compra_inventario")

    def __str__(self):
        return f"Compra {self.insumo.nombre} · {self.cantidad} {self.insumo.unidad_corta}"

    class Meta:
        verbose_name = "Compra de inventario"
        verbose_name_plural = "Compras de inventario"
        ordering = ["-fecha", "-id"]


class EntradaStock(models.Model):
    insumo = models.ForeignKey(Insumo, on_delete=models.CASCADE, related_name="entradas_stock")
    cantidad = models.DecimalField(max_digits=12, decimal_places=3)
    observacion = models.CharField(max_length=255, blank=True)
    fecha = models.DateField(auto_now_add=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Entrada {self.insumo.nombre} {self.cantidad} {self.insumo.unidad_corta}"

    class Meta:
        verbose_name = "Entrada de stock"
        verbose_name_plural = "Entradas de stock"
        ordering = ["-fecha", "-id"]


class MovimientoInventario(models.Model):
    TIPO_CHOICES = [
        ("compra", "Compra"),
        ("entrada", "Entrada / ajuste +"),
        ("venta", "Venta"),
        ("entrega", "Entrega a trabajador"),
        ("devolucion", "Devolución de trabajador"),
        ("mantenimiento", "Consumo en mantenimiento"),
        ("ajuste", "Ajuste"),
    ]

    insumo = models.ForeignKey(Insumo, on_delete=models.PROTECT, related_name="movimientos")
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, db_index=True)
    cantidad = models.DecimalField(max_digits=12, decimal_places=3)
    stock_anterior = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    stock_resultante = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    trabajador = models.ForeignKey("trabajadores.Trabajador", on_delete=models.SET_NULL, null=True, blank=True, related_name="movimientos_inventario")
    stock_trabajador_anterior = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    stock_trabajador_resultante = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    mantenimiento = models.ForeignKey("mantenimientos.Mantenimiento", on_delete=models.SET_NULL, null=True, blank=True, related_name="movimientos_inventario")
    costo_unitario = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    total_costo = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="movimientos_inventario_registrados")
    observacion = models.CharField(max_length=255, blank=True)
    fecha = models.DateField(auto_now_add=True, db_index=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_tipo_display()} · {self.insumo.nombre} · {self.cantidad} {self.insumo.unidad_corta}"

    class Meta:
        verbose_name = "Movimiento de inventario"
        verbose_name_plural = "Movimientos de inventario"
        ordering = ["-creado_en", "-id"]
