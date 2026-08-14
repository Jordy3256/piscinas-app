from datetime import date
from decimal import Decimal

from django.db import models
from django.utils import timezone

from inventario.models import Insumo
from clientes.models import Cliente
from contratos.models import Contrato


# =====================================================
# EGRESOS
# =====================================================
class Egreso(models.Model):
    mantenimiento = models.ForeignKey(
        'mantenimientos.Mantenimiento',
        on_delete=models.CASCADE,
        related_name='egresos',
        null=True,
        blank=True
    )
    insumo = models.ForeignKey(
        Insumo,
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )

    concepto = models.CharField(max_length=120, blank=True, default="")
    categoria = models.CharField(max_length=80, blank=True, default="")

    cantidad = models.PositiveIntegerField(default=1)
    costo_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    fecha = models.DateField(default=date.today)

    @property
    def es_manual(self):
        return not self.mantenimiento_id and not self.insumo_id

    def save(self, *args, **kwargs):
        self.total = self.cantidad * self.costo_unitario
        super().save(*args, **kwargs)

    def __str__(self):
        if self.concepto:
            return f"{self.concepto} - {self.total}"
        if self.insumo:
            return f"{self.insumo.nombre} - {self.total}"
        return f"Egreso - {self.total}"

    class Meta:
        verbose_name = "Egreso"
        verbose_name_plural = "Egresos"
        ordering = ["-fecha", "-id"]


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


# =====================================================
# FACTURAS
# =====================================================
class Factura(models.Model):
    ESTADO_PENDIENTE = "pendiente"
    ESTADO_PAGADA = "pagada"
    ESTADO_VENCIDA = "vencida"
    ESTADO_ANULADA = "anulada"

    ESTADO_CHOICES = [
        (ESTADO_PENDIENTE, "Pendiente"),
        (ESTADO_PAGADA, "Pagada"),
        (ESTADO_VENCIDA, "Vencida"),
        (ESTADO_ANULADA, "Anulada"),
    ]

    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.PROTECT,
        related_name="facturas"
    )
    contrato = models.ForeignKey(
        Contrato,
        on_delete=models.PROTECT,
        related_name="facturas"
    )

    numero = models.CharField(max_length=30, unique=True, blank=True)
    periodo_anio = models.PositiveIntegerField()
    periodo_mes = models.PositiveIntegerField()

    fecha_emision = models.DateField(default=date.today)
    fecha_vencimiento = models.DateField()

    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    impuesto = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    estado = models.CharField(
        max_length=10,
        choices=ESTADO_CHOICES,
        default=ESTADO_PENDIENTE
    )
    observaciones = models.TextField(blank=True, default="")

    ingreso_generado = models.OneToOneField(
        Ingreso,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="factura_origen"
    )

    pagada_en = models.DateField(null=True, blank=True)
    creada_en = models.DateTimeField(auto_now_add=True)
    actualizada_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Factura"
        verbose_name_plural = "Facturas"
        ordering = ["-periodo_anio", "-periodo_mes", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["contrato", "periodo_anio", "periodo_mes"],
                name="unique_factura_por_contrato_y_periodo"
            )
        ]

    def __str__(self):
        return f"{self.numero or 'Factura'} - {self.cliente} - {self.periodo_mes:02d}/{self.periodo_anio}"

    @property
    def periodo_label(self):
        return f"{self.periodo_mes:02d}/{self.periodo_anio}"

    @property
    def esta_vencida(self):
        return (
            self.estado == self.ESTADO_PENDIENTE and
            self.fecha_vencimiento < timezone.localdate()
        )

    def actualizar_totales(self, guardar=True):
        subtotal = sum(
            (item.subtotal for item in self.items.all()),
            Decimal("0")
        )
        self.subtotal = subtotal
        self.total = subtotal + (self.impuesto or Decimal("0"))

        if guardar:
            self.save(update_fields=["subtotal", "total", "actualizada_en"])

    def marcar_como_pagada(self, fecha_pago=None):
        if self.estado == self.ESTADO_PAGADA:
            return self.ingreso_generado

        fecha_pago = fecha_pago or timezone.localdate()

        ingreso = self.ingreso_generado
        if not ingreso:
            ingreso = Ingreso.objects.create(
                cliente=self.cliente,
                contrato=self.contrato,
                concepto=f"Pago factura {self.numero} - {self.periodo_label}",
                total=self.total,
                fecha=fecha_pago,
            )

        self.estado = self.ESTADO_PAGADA
        self.pagada_en = fecha_pago
        self.ingreso_generado = ingreso
        self.save(update_fields=["estado", "pagada_en", "ingreso_generado", "actualizada_en"])
        return ingreso

    def marcar_como_vencida_si_aplica(self, guardar=True):
        if self.esta_vencida:
            self.estado = self.ESTADO_VENCIDA
            if guardar:
                self.save(update_fields=["estado", "actualizada_en"])

    def save(self, *args, **kwargs):
        es_nueva = self.pk is None

        if self.numero is None:
            self.numero = ""

        self.total = (self.subtotal or Decimal("0")) + (self.impuesto or Decimal("0"))

        if self.estado == self.ESTADO_PENDIENTE and self.fecha_vencimiento < timezone.localdate():
            self.estado = self.ESTADO_VENCIDA

        super().save(*args, **kwargs)

        numero_esperado = f"FAC-{self.periodo_anio}{self.periodo_mes:02d}-{self.pk:05d}"
        if self.numero != numero_esperado:
            self.numero = numero_esperado
            super().save(update_fields=["numero", "actualizada_en"] if not es_nueva else ["numero"])


class FacturaItem(models.Model):
    factura = models.ForeignKey(
        Factura,
        on_delete=models.CASCADE,
        related_name="items"
    )
    descripcion = models.CharField(max_length=255)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        verbose_name = "Ítem de factura"
        verbose_name_plural = "Ítems de factura"
        ordering = ["id"]

    def __str__(self):
        return self.descripcion

    def save(self, *args, **kwargs):
        self.subtotal = (self.cantidad or Decimal("0")) * (self.precio_unitario or Decimal("0"))
        super().save(*args, **kwargs)
        self.factura.actualizar_totales()

    def delete(self, *args, **kwargs):
        factura = self.factura
        super().delete(*args, **kwargs)
        factura.actualizar_totales()