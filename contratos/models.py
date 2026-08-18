from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from clientes.models import Cliente
from trabajadores.models import Trabajador


def _mover_mes(anio, mes, desplazamiento=1):
    indice = (anio * 12 + (mes - 1)) + desplazamiento
    return indice // 12, indice % 12 + 1


def _fecha_segura(anio, mes, dia):
    return date(anio, mes, min(max(int(dia or 1), 1), monthrange(anio, mes)[1]))


class Contrato(models.Model):
    TIPO_CHOICES = [
        ("semanal", "Semanal"),
        ("quincenal", "Quincenal"),
        ("mensual", "Mensual"),
        ("variable", "Variable"),
    ]

    FRECUENCIA_CHOICES = [
        ("1_semanal", "1 visita semanal"),
        ("2_semanales", "2 visitas semanales"),
        ("3_semanales", "3 visitas semanales"),
        ("quincenal", "Cada 15 días"),
        ("personalizado", "Personalizado"),
    ]

    FORMA_PAGO_CHOICES = [
        ("adelantado", "Adelantado"),
        ("servicio_cumplido", "Servicio cumplido"),
        ("50_50", "50/50"),
        ("quincenal", "Quincenal"),
        ("por_visita", "Por visita"),
        ("fin_mensualidad", "Fin de la mensualidad"),
        ("personalizado", "Personalizado"),
    ]

    PROGRAMACION_COBRO_CHOICES = [
        ("inicio_periodo", "Mismo día de inicio del periodo"),
        ("cierre_periodo", "Mismo día de cierre del periodo"),
        ("dia_fijo", "Día fijo mensual"),
        ("rango_dias", "Rango de días"),
        ("dos_pagos", "Dos pagos mensuales"),
        ("despues_cierre", "Días después del cierre"),
        ("personalizado", "Personalizado"),
    ]


    QUIMICOS_PROVEEDOR_CHOICES = [
        ("jvaqua", "JVAQUA"),
        ("cliente", "Cliente"),
    ]

    QUIMICOS_ALMACENAMIENTO_CHOICES = [
        ("trabajador", "Inventario del trabajador"),
        ("contrato", "Inventario del contrato (en sitio)"),
    ]

    MOMENTO_FACTURACION_CHOICES = [
        ("antes_inicio", "Antes de iniciar el periodo"),
        ("inicio_periodo", "Al iniciar el periodo"),
        ("cierre_periodo", "Al finalizar el periodo"),
        ("dia_fijo", "Día fijo del mes"),
        ("antes_cobro", "Días antes del cobro"),
        ("personalizado", "Personalizado"),
    ]

    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name="contratos")
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    frecuencia = models.CharField(max_length=30, choices=FRECUENCIA_CHOICES, blank=True, default="")
    frecuencia_personalizada = models.CharField(max_length=150, blank=True, default="")

    # Condición comercial. No contiene fechas.
    forma_pago = models.CharField(max_length=30, choices=FORMA_PAGO_CHOICES, blank=True, default="")
    forma_pago_personalizada = models.CharField(max_length=150, blank=True, default="")

    # Campo anterior conservado por compatibilidad. Se sincroniza con cobro_dia_1.
    dia_pago = models.PositiveSmallIntegerField(null=True, blank=True)

    # Periodo del servicio.
    periodo_dia_inicio = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(31)],
        help_text="Día en que inicia cada periodo mensual del servicio.",
    )

    # Programación independiente de cobros.
    programacion_cobro = models.CharField(
        max_length=30,
        choices=PROGRAMACION_COBRO_CHOICES,
        default="inicio_periodo",
    )
    cobro_mes_desfase = models.PositiveSmallIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(2)],
        help_text="0 = mes del inicio del periodo; 1 = mes siguiente; 2 = dos meses después.",
    )
    cobro_dia_1 = models.PositiveSmallIntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(31)])
    cobro_dia_2 = models.PositiveSmallIntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(31)])
    cobro_rango_desde = models.PositiveSmallIntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(31)])
    cobro_rango_hasta = models.PositiveSmallIntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(31)])
    cobro_dias_despues_cierre = models.PositiveSmallIntegerField(default=0)
    porcentaje_primer_pago = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("50.00"),
        validators=[MinValueValidator(Decimal("0.01")), MaxValueValidator(Decimal("99.99"))],
    )
    programacion_cobro_personalizada = models.CharField(max_length=200, blank=True, default="")

    # Facturación independiente del calendario de cobro.
    requiere_factura = models.BooleanField(default=False)
    momento_facturacion = models.CharField(
        max_length=30,
        choices=MOMENTO_FACTURACION_CHOICES,
        blank=True,
        default="",
    )
    facturacion_dia = models.PositiveSmallIntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(31)])
    facturacion_dias_antes = models.PositiveSmallIntegerField(default=0)
    notificar_facturacion = models.BooleanField(default=False)
    notificacion_factura_dias_antes = models.PositiveSmallIntegerField(default=1)
    observaciones_facturacion = models.TextField(blank=True, default="")

    precio_mensual = models.DecimalField(max_digits=10, decimal_places=2)
    valor_tecnico_mensual = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    fecha_inicio = models.DateField()
    tecnico_designado = models.ForeignKey(
        Trabajador,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contratos_designados",
    )
    dias_visita = models.JSONField(default=list, blank=True)
    generacion_automatica = models.BooleanField(default=True)
    programado_hasta = models.DateField(null=True, blank=True)
    activo = models.BooleanField(default=True)
    MOTIVO_BAJA_CHOICES = [
        ("precio", "Precio"),
        ("mudanza_venta", "Cliente vendió o se mudó"),
        ("piscina_fuera_uso", "Piscina fuera de uso"),
        ("mala_experiencia", "Mala experiencia"),
        ("cambio_proveedor", "Cambio de proveedor"),
        ("mantenimiento_propio", "Cliente realizará mantenimiento propio"),
        ("morosidad", "Morosidad"),
        ("servicio_temporal", "Servicio temporal finalizado"),
        ("otro", "Otro"),
        ("no_especificado", "No especificado"),
    ]
    fecha_baja = models.DateField(null=True, blank=True, db_index=True)
    motivo_baja = models.CharField(max_length=30, choices=MOTIVO_BAJA_CHOICES, blank=True, default="")
    motivo_baja_detalle = models.CharField(max_length=250, blank=True, default="")

    # Gestión logística de químicos por contrato.
    quimicos_proveedor = models.CharField(
        max_length=20,
        choices=QUIMICOS_PROVEEDOR_CHOICES,
        default="jvaqua",
        help_text="Indica si los químicos son proporcionados por JVAQUA o por el cliente.",
    )
    quimicos_almacenamiento = models.CharField(
        max_length=20,
        choices=QUIMICOS_ALMACENAMIENTO_CHOICES,
        default="trabajador",
        blank=True,
        help_text="Cuando JVAQUA proporciona químicos, indica dónde se almacenan.",
    )
    HORARIO_VISITA_CHOICES = [
        ("libre", "Horario libre"),
        ("fijo", "Hora fija"),
        ("ventana", "Ventana horaria"),
    ]

    PRIORIDAD_VISITA_CHOICES = [
        ("normal", "Normal"),
        ("alta", "Alta"),
    ]

    tipo_horario_visita = models.CharField(
        max_length=20, choices=HORARIO_VISITA_CHOICES, default="libre",
        help_text="Restricción horaria usada únicamente para sugerir la ruta diaria al técnico.",
    )
    hora_visita_fija = models.TimeField(null=True, blank=True)
    ventana_visita_desde = models.TimeField(null=True, blank=True)
    ventana_visita_hasta = models.TimeField(null=True, blank=True)
    duracion_estimada_minutos = models.PositiveSmallIntegerField(
        default=30, validators=[MinValueValidator(10), MaxValueValidator(480)],
        help_text="Duración orientativa del mantenimiento para planificar la ruta.",
    )
    prioridad_visita = models.CharField(
        max_length=10, choices=PRIORIDAD_VISITA_CHOICES, default="normal"
    )

    responsable_reposicion = models.ForeignKey(
        Trabajador,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contratos_reposicion",
        help_text="Responsable principal de reponer el inventario en sitio. Si se deja vacío, se usa el técnico designado.",
    )

    def ingreso_mensual(self):
        return self.precio_mensual

    def frecuencia_completa(self):
        if self.frecuencia == "personalizado":
            return self.frecuencia_personalizada or "Personalizada"
        if self.frecuencia:
            return self.get_frecuencia_display()
        equivalencias = {"semanal": "Semanal", "quincenal": "Cada 15 días", "mensual": "Mensual", "variable": "Variable"}
        return equivalencias.get(self.tipo, self.tipo or "Sin definir")

    frecuencia_completa.short_description = "Frecuencia"

    def forma_pago_completa(self):
        if self.forma_pago == "personalizado":
            return self.forma_pago_personalizada or "Personalizada"
        return self.get_forma_pago_display() if self.forma_pago else "Sin definir"

    forma_pago_completa.short_description = "Forma de pago"

    def dias_visita_completos(self):
        nombres = {0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves", 4: "Viernes", 5: "Sábado", 6: "Domingo"}
        dias = []
        for valor in self.dias_visita or []:
            try:
                numero = int(valor)
            except (TypeError, ValueError):
                continue
            if numero in nombres and numero not in dias:
                dias.append(numero)
        return ", ".join(nombres[dia] for dia in sorted(dias)) or "Sin definir"

    dias_visita_completos.short_description = "Días de visita"

    def periodo_servicio(self, anio, mes):
        inicio = _fecha_segura(anio, mes, self.periodo_dia_inicio or self.fecha_inicio.day)
        anio_fin, mes_fin = _mover_mes(anio, mes, 1)
        fin = _fecha_segura(anio_fin, mes_fin, self.periodo_dia_inicio or self.fecha_inicio.day)
        return inicio, fin

    def calendario_cobros(self, anio, mes):
        """Devuelve cuotas para el periodo indicado sin escribir en la base."""
        inicio, fin = self.periodo_servicio(anio, mes)
        programacion = self.programacion_cobro or "inicio_periodo"
        destino_anio, destino_mes = _mover_mes(anio, mes, int(self.cobro_mes_desfase or 0))

        if programacion == "inicio_periodo":
            fechas = [(inicio, inicio)]
        elif programacion == "cierre_periodo":
            fechas = [(fin, fin)]
        elif programacion == "dia_fijo":
            fecha = _fecha_segura(destino_anio, destino_mes, self.cobro_dia_1 or self.dia_pago or inicio.day)
            fechas = [(fecha, fecha)]
        elif programacion == "rango_dias":
            desde = _fecha_segura(destino_anio, destino_mes, self.cobro_rango_desde or 1)
            hasta = _fecha_segura(destino_anio, destino_mes, self.cobro_rango_hasta or self.cobro_rango_desde or 1)
            if hasta < desde:
                hasta = desde
            fechas = [(desde, hasta)]
        elif programacion == "dos_pagos":
            f1 = _fecha_segura(destino_anio, destino_mes, self.cobro_dia_1 or 1)
            f2 = _fecha_segura(destino_anio, destino_mes, self.cobro_dia_2 or 15)
            if f2 < f1:
                f1, f2 = f2, f1
            fechas = [(f1, f1), (f2, f2)]
        elif programacion == "despues_cierre":
            fecha = fin + timedelta(days=int(self.cobro_dias_despues_cierre or 0))
            fechas = [(fecha, fecha)]
        else:
            fecha = _fecha_segura(destino_anio, destino_mes, self.cobro_dia_1 or inicio.day)
            fechas = [(fecha, fecha)]

        if len(fechas) == 2:
            porcentaje_1 = Decimal(self.porcentaje_primer_pago or Decimal("50.00"))
            valor_1 = (self.precio_mensual * porcentaje_1 / Decimal("100")).quantize(Decimal("0.01"))
            valores = [valor_1, self.precio_mensual - valor_1]
        else:
            valores = [self.precio_mensual]

        return [
            {
                "cuota_numero": indice,
                "total_cuotas": len(fechas),
                "fecha_cobro_desde": ventana[0],
                "fecha_vencimiento": ventana[1],
                "valor": valores[indice - 1],
                "periodo_inicio": inicio,
                "periodo_fin": fin,
            }
            for indice, ventana in enumerate(fechas, start=1)
        ]

    def fecha_programada_facturacion(self, anio, mes):
        if not self.requiere_factura:
            return None
        inicio, fin = self.periodo_servicio(anio, mes)
        primer_cobro = self.calendario_cobros(anio, mes)[0]["fecha_cobro_desde"]
        momento = self.momento_facturacion or "antes_cobro"
        if momento == "antes_inicio":
            return inicio - timedelta(days=int(self.facturacion_dias_antes or 0))
        if momento == "inicio_periodo":
            return inicio
        if momento == "cierre_periodo":
            return fin
        if momento == "dia_fijo":
            destino_anio, destino_mes = primer_cobro.year, primer_cobro.month
            return _fecha_segura(destino_anio, destino_mes, self.facturacion_dia or 1)
        if momento == "antes_cobro":
            return primer_cobro - timedelta(days=int(self.facturacion_dias_antes or 0))
        return _fecha_segura(primer_cobro.year, primer_cobro.month, self.facturacion_dia or primer_cobro.day)

    def sincronizar_tipo_compatibilidad(self):
        equivalencias = {"1_semanal": "semanal", "2_semanales": "semanal", "3_semanales": "semanal", "quincenal": "quincenal", "personalizado": "variable"}
        if self.frecuencia in equivalencias:
            self.tipo = equivalencias[self.frecuencia]

    def save(self, *args, **kwargs):
        self.frecuencia_personalizada = (self.frecuencia_personalizada or "").strip()
        self.forma_pago_personalizada = (self.forma_pago_personalizada or "").strip()
        self.programacion_cobro_personalizada = (self.programacion_cobro_personalizada or "").strip()
        self.observaciones_facturacion = (self.observaciones_facturacion or "").strip()
        if self.quimicos_proveedor == "cliente":
            self.quimicos_almacenamiento = ""
            self.responsable_reposicion = None
        elif self.quimicos_almacenamiento not in {"trabajador", "contrato"}:
            self.quimicos_almacenamiento = "trabajador"
        if self.frecuencia != "personalizado":
            self.frecuencia_personalizada = ""
        if self.forma_pago != "personalizado":
            self.forma_pago_personalizada = ""
        if self.programacion_cobro != "personalizado":
            self.programacion_cobro_personalizada = ""
        if self.programacion_cobro == "dia_fijo":
            self.dia_pago = self.cobro_dia_1
        else:
            self.dia_pago = None
        if not self.requiere_factura:
            self.momento_facturacion = ""
            self.facturacion_dia = None
            self.notificar_facturacion = False
            self.observaciones_facturacion = ""
        self.sincronizar_tipo_compatibilidad()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.cliente} - {self.frecuencia_completa()}"

    class Meta:
        verbose_name = "Contrato"
        verbose_name_plural = "Contratos"
        ordering = ["-activo", "cliente__nombre", "id"]
