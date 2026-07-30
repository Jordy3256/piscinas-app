from datetime import date
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from clientes.models import Cliente
from contratos.models import Contrato
from inventario.models import Insumo


class MovimientoFinancieroMixin(models.Model):
    ESTADO_PENDIENTE = "pendiente"
    ESTADO_PARCIAL = "parcial"
    ESTADO_PAGADO = "pagado"
    ESTADO_VENCIDO = "vencido"
    ESTADO_ANULADO = "anulado"

    ESTADO_CHOICES = [
        (ESTADO_PENDIENTE, "Pendiente"),
        (ESTADO_PARCIAL, "Parcial"),
        (ESTADO_PAGADO, "Pagado"),
        (ESTADO_VENCIDO, "Vencido"),
        (ESTADO_ANULADO, "Anulado"),
    ]

    METODO_CHOICES = [
        ("efectivo", "Efectivo"),
        ("transferencia", "Transferencia"),
        ("tarjeta", "Tarjeta"),
        ("deposito", "Depósito"),
        ("cheque", "Cheque"),
        ("otro", "Otro"),
    ]

    estado = models.CharField(
        max_length=12,
        choices=ESTADO_CHOICES,
        default=ESTADO_PAGADO,
        db_index=True,
    )
    monto_pagado = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    fecha_vencimiento = models.DateField(null=True, blank=True, db_index=True)
    metodo_pago = models.CharField(max_length=20, choices=METODO_CHOICES, blank=True, default="")
    comprobante = models.FileField(upload_to="finanzas/comprobantes/%Y/%m/", null=True, blank=True)
    observaciones = models.TextField(blank=True, default="")
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_creados",
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    @property
    def saldo(self):
        if self.estado == self.ESTADO_ANULADO:
            return Decimal("0.00")
        return max((self.total or Decimal("0.00")) - (self.monto_pagado or Decimal("0.00")), Decimal("0.00"))

    @property
    def porcentaje_pagado(self):
        total = self.total or Decimal("0.00")
        if total <= 0:
            return 0
        return min(100, int(((self.monto_pagado or Decimal("0.00")) / total) * 100))

    @property
    def estado_visual(self):
        if (
            self.estado in {self.ESTADO_PENDIENTE, self.ESTADO_PARCIAL}
            and self.fecha_vencimiento
            and self.fecha_vencimiento < timezone.localdate()
        ):
            return self.ESTADO_VENCIDO
        return self.estado

    def _normalizar_estado_pago(self):
        total = self.total or Decimal("0.00")
        pagado = self.monto_pagado or Decimal("0.00")
        pagado = max(Decimal("0.00"), min(pagado, total))
        self.monto_pagado = pagado

        if self.estado == self.ESTADO_ANULADO:
            return
        if total > 0 and pagado >= total:
            self.estado = self.ESTADO_PAGADO
        elif pagado > 0:
            self.estado = self.ESTADO_PARCIAL
        elif self.fecha_vencimiento and self.fecha_vencimiento < timezone.localdate():
            self.estado = self.ESTADO_VENCIDO
        else:
            self.estado = self.ESTADO_PENDIENTE


class Egreso(MovimientoFinancieroMixin):
    CATEGORIA_CHOICES = [
        ("quimicos", "Químicos"),
        ("tecnicos", "Sueldos y pagos a técnicos"),
        ("transporte", "Transporte"),
        ("alimentacion", "Alimentación"),
        ("hospedaje", "Hospedaje"),
        ("materiales", "Materiales"),
        ("herramientas", "Herramientas"),
        ("reparaciones", "Reparaciones"),
        ("publicidad", "Publicidad"),
        ("servicios", "Servicios"),
        ("administracion", "Administración"),
        ("otros", "Otros gastos"),
    ]

    mantenimiento = models.ForeignKey(
        "mantenimientos.Mantenimiento",
        on_delete=models.CASCADE,
        related_name="egresos",
        null=True,
        blank=True,
    )
    insumo = models.ForeignKey(Insumo, on_delete=models.PROTECT, null=True, blank=True)
    concepto = models.CharField(max_length=120, blank=True, default="")
    categoria = models.CharField(max_length=30, choices=CATEGORIA_CHOICES, blank=True, default="otros", db_index=True)
    cantidad = models.PositiveIntegerField(default=1)
    costo_unitario = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    fecha = models.DateField(default=date.today, db_index=True)
    proveedor = models.CharField(max_length=150, blank=True, default="")
    ciudad_proyecto = models.CharField(max_length=120, blank=True, default="")
    aprobado = models.BooleanField(default=True, db_index=True)

    @property
    def es_manual(self):
        return not self.mantenimiento_id and not self.insumo_id

    def save(self, *args, **kwargs):
        self.total = (self.cantidad or 0) * (self.costo_unitario or Decimal("0.00"))
        if self._state.adding and self.estado == self.ESTADO_PAGADO and not self.monto_pagado:
            self.monto_pagado = self.total
        self._normalizar_estado_pago()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.concepto or (self.insumo.nombre if self.insumo else 'Egreso')} - {self.total}"

    class Meta:
        verbose_name = "Egreso"
        verbose_name_plural = "Egresos"
        ordering = ["-fecha", "-id"]


class Ingreso(MovimientoFinancieroMixin):
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, null=True, blank=True, related_name="ingresos")
    contrato = models.ForeignKey(Contrato, on_delete=models.PROTECT, null=True, blank=True, related_name="ingresos")
    concepto = models.CharField(max_length=120)
    total = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    fecha = models.DateField(default=date.today, db_index=True)
    fecha_cobro = models.DateField(null=True, blank=True)
    ciudad = models.CharField(max_length=120, blank=True, default="")

    def save(self, *args, **kwargs):
        if self._state.adding and self.estado == self.ESTADO_PAGADO and not self.monto_pagado:
            self.monto_pagado = self.total
        self._normalizar_estado_pago()
        if self.estado == self.ESTADO_PAGADO and not self.fecha_cobro:
            self.fecha_cobro = self.fecha
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.fecha} - {self.concepto} - {self.total}"

    class Meta:
        verbose_name = "Ingreso"
        verbose_name_plural = "Ingresos"
        ordering = ["-fecha", "-id"]


class MovimientoRecurrente(models.Model):
    TIPO_CHOICES = [("ingreso", "Ingreso"), ("egreso", "Egreso")]
    FRECUENCIA_CHOICES = [("mensual", "Mensual"), ("semanal", "Semanal")]

    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    concepto = models.CharField(max_length=120)
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    frecuencia = models.CharField(max_length=10, choices=FRECUENCIA_CHOICES, default="mensual")
    proxima_fecha = models.DateField()
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.tipo.upper()} - {self.concepto} - {self.monto}"

    class Meta:
        verbose_name = "Movimiento recurrente"
        verbose_name_plural = "Movimientos recurrentes"


class Factura(models.Model):
    ESTADO_PENDIENTE = "pendiente"
    ESTADO_PARCIAL = "parcial"
    ESTADO_PAGADA = "pagada"
    ESTADO_VENCIDA = "vencida"
    ESTADO_ANULADA = "anulada"
    ESTADO_CHOICES = [
        (ESTADO_PENDIENTE, "Pendiente"),
        (ESTADO_PARCIAL, "Parcial"),
        (ESTADO_PAGADA, "Pagada"),
        (ESTADO_VENCIDA, "Vencida"),
        (ESTADO_ANULADA, "Anulada"),
    ]

    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name="facturas")
    contrato = models.ForeignKey(Contrato, on_delete=models.PROTECT, related_name="facturas")
    numero = models.CharField(max_length=30, unique=True, blank=True)
    periodo_anio = models.PositiveIntegerField()
    periodo_mes = models.PositiveIntegerField()
    fecha_emision = models.DateField(default=date.today)
    fecha_vencimiento = models.DateField()
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    impuesto = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default=ESTADO_PENDIENTE)
    observaciones = models.TextField(blank=True, default="")
    ingreso_generado = models.OneToOneField(
        Ingreso, on_delete=models.SET_NULL, null=True, blank=True, related_name="factura_origen"
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
                name="unique_factura_por_contrato_y_periodo",
            )
        ]

    def __str__(self):
        return f"{self.numero or 'Factura'} - {self.cliente} - {self.periodo_mes:02d}/{self.periodo_anio}"

    @property
    def periodo_label(self):
        return f"{self.periodo_mes:02d}/{self.periodo_anio}"

    @property
    def esta_vencida(self):
        return self.estado in {self.ESTADO_PENDIENTE, self.ESTADO_PARCIAL} and self.fecha_vencimiento < timezone.localdate()

    @property
    def monto_pagado(self):
        """Total cobrado, conservando compatibilidad con facturas antiguas."""
        total_pagos = self.pagos.filter(activo=True).aggregate(valor=models.Sum("monto"))["valor"] or Decimal("0.00")
        if total_pagos == 0 and self.ingreso_generado_id and self.estado == self.ESTADO_PAGADA:
            return self.total or Decimal("0.00")
        return total_pagos

    @property
    def saldo(self):
        if self.estado == self.ESTADO_ANULADA:
            return Decimal("0.00")
        return max((self.total or Decimal("0.00")) - self.monto_pagado, Decimal("0.00"))

    @property
    def porcentaje_pagado(self):
        if not self.total:
            return 0
        return min(100, int((self.monto_pagado / self.total) * 100))

    @property
    def estado_visual(self):
        if self.estado not in {self.ESTADO_PAGADA, self.ESTADO_ANULADA} and self.fecha_vencimiento < timezone.localdate():
            return self.ESTADO_VENCIDA
        return self.estado

    def sincronizar_estado(self, guardar=True):
        if self.estado == self.ESTADO_ANULADA:
            return self.estado
        pagado = self.monto_pagado
        if self.total > 0 and pagado >= self.total:
            nuevo = self.ESTADO_PAGADA
        elif pagado > 0:
            nuevo = self.ESTADO_PARCIAL
        elif self.fecha_vencimiento < timezone.localdate():
            nuevo = self.ESTADO_VENCIDA
        else:
            nuevo = self.ESTADO_PENDIENTE
        self.estado = nuevo
        self.pagada_en = timezone.localdate() if nuevo == self.ESTADO_PAGADA and not self.pagada_en else (None if nuevo != self.ESTADO_PAGADA else self.pagada_en)
        if guardar:
            self.save(update_fields=["estado", "pagada_en", "actualizada_en"])
        return nuevo

    def actualizar_totales(self, guardar=True):
        subtotal = sum((item.subtotal for item in self.items.all()), Decimal("0"))
        self.subtotal = subtotal
        self.total = subtotal + (self.impuesto or Decimal("0"))
        if guardar:
            self.save(update_fields=["subtotal", "total", "actualizada_en"])

    def marcar_como_pagada(self, fecha_pago=None):
        """Compatibilidad: registra un pago por el saldo completo."""
        if self.estado == self.ESTADO_PAGADA or self.saldo <= 0:
            return self.ingreso_generado
        pago = PagoFactura.objects.create(
            factura=self,
            monto=self.saldo,
            fecha=fecha_pago or timezone.localdate(),
            metodo_pago="otro",
            observaciones="Pago total registrado desde compatibilidad anterior.",
        )
        return pago.ingreso

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
    factura = models.ForeignKey(Factura, on_delete=models.CASCADE, related_name="items")
    descripcion = models.CharField(max_length=180)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        self.subtotal = (self.cantidad or Decimal("0")) * (self.precio_unitario or Decimal("0"))
        super().save(*args, **kwargs)
        self.factura.actualizar_totales()

    def delete(self, *args, **kwargs):
        factura = self.factura
        super().delete(*args, **kwargs)
        factura.actualizar_totales()

    def __str__(self):
        return self.descripcion


class PagoFactura(models.Model):
    factura = models.ForeignKey(Factura, on_delete=models.PROTECT, related_name="pagos")
    monto = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    fecha = models.DateField(default=date.today, db_index=True)
    metodo_pago = models.CharField(max_length=20, choices=MovimientoFinancieroMixin.METODO_CHOICES, default="transferencia")
    referencia = models.CharField(max_length=120, blank=True, default="")
    comprobante = models.FileField(upload_to="finanzas/pagos_facturas/%Y/%m/", null=True, blank=True)
    observaciones = models.TextField(blank=True, default="")
    ingreso = models.OneToOneField(Ingreso, on_delete=models.SET_NULL, null=True, blank=True, related_name="pago_factura")
    activo = models.BooleanField(default=True, db_index=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="pagos_factura_creados")
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Pago de factura"
        verbose_name_plural = "Pagos de facturas"
        ordering = ["-fecha", "-id"]

    def __str__(self):
        return f"{self.factura.numero} - {self.monto}"

    def save(self, *args, **kwargs):
        creando = self._state.adding
        if self.factura_id and self.activo:
            saldo_disponible = self.factura.saldo
            if not creando:
                anterior = PagoFactura.objects.filter(pk=self.pk).values("monto", "activo").first()
                if anterior and anterior["activo"]:
                    saldo_disponible += anterior["monto"]
            if self.monto > saldo_disponible:
                from django.core.exceptions import ValidationError
                raise ValidationError({"monto": f"El pago no puede superar el saldo pendiente de ${saldo_disponible:.2f}."})
        super().save(*args, **kwargs)

        if self.activo:
            ingreso = self.ingreso
            datos = {
                "cliente": self.factura.cliente,
                "contrato": self.factura.contrato,
                "concepto": f"Cobro {self.factura.numero} - {self.factura.periodo_label}",
                "total": self.monto,
                "monto_pagado": self.monto,
                "estado": Ingreso.ESTADO_PAGADO,
                "fecha": self.fecha,
                "fecha_cobro": self.fecha,
                "metodo_pago": self.metodo_pago,
                "comprobante": self.comprobante,
                "observaciones": self.observaciones,
                "creado_por": self.creado_por,
            }
            if ingreso:
                for campo, valor in datos.items():
                    setattr(ingreso, campo, valor)
                ingreso.save()
            else:
                self.ingreso = Ingreso.objects.create(**datos)
                super().save(update_fields=["ingreso", "actualizado_en"])
        elif self.ingreso_id and self.ingreso.estado != Ingreso.ESTADO_ANULADO:
            self.ingreso.estado = Ingreso.ESTADO_ANULADO
            self.ingreso.monto_pagado = Decimal("0.00")
            self.ingreso.save(update_fields=["estado", "monto_pagado", "actualizado_en"])

        self.factura.sincronizar_estado()

    def anular(self):
        if not self.activo:
            return
        self.activo = False
        self.save(update_fields=["activo", "actualizado_en"])
