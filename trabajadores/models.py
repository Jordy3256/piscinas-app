from django.db import models
from django.contrib.auth.models import User


class Trabajador(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    class Meta:
        verbose_name = "Trabajador"
        verbose_name_plural = "Trabajadores"
    telefono = models.CharField(max_length=20)
    activo = models.BooleanField(default=True)

    FORMA_PAGO_CHOICES = [
        ("fin_mes", "Al finalizar el mes"),
        ("adelantado", "Por adelantado"),
        ("semanal", "Semanal"),
        ("quincenal", "Quincenal"),
        ("por_visita", "Por visita"),
        ("por_contrato", "Por contrato"),
        ("personalizado", "Personalizado"),
    ]
    PROGRAMACION_PAGO_CHOICES = [
        ("fin_periodo", "Al finalizar el período de servicio"),
        ("fecha_contratos", "Mismas fechas de cobro de los contratos"),
        ("dia_fijo", "Día fijo mensual"),
        ("rango", "Rango de días"),
        ("personalizado", "Personalizado"),
    ]
    MODALIDAD_PAGO_CHOICES = [
        ("unico", "Un solo pago consolidado"),
        ("dos_pagos", "Dos pagos"),
        ("parciales", "Pagos parciales"),
        ("personalizado", "Personalizado"),
    ]
    forma_pago_nomina = models.CharField(max_length=20, choices=FORMA_PAGO_CHOICES, default="fin_mes")
    programacion_pago_nomina = models.CharField(max_length=25, choices=PROGRAMACION_PAGO_CHOICES, default="fecha_contratos")
    modalidad_pago_nomina = models.CharField(max_length=20, choices=MODALIDAD_PAGO_CHOICES, default="unico")
    dia_pago_nomina = models.PositiveSmallIntegerField(null=True, blank=True)
    dia_pago_desde = models.PositiveSmallIntegerField(null=True, blank=True)
    dia_pago_hasta = models.PositiveSmallIntegerField(null=True, blank=True)
    segundo_dia_pago = models.PositiveSmallIntegerField(null=True, blank=True)
    dias_despues_fin_periodo = models.PositiveSmallIntegerField(
        default=0,
        help_text="Días adicionales después del cierre del período de servicio para programar el pago.",
    )
    observaciones_pago = models.TextField(blank=True, default="")
    fecha_ingreso = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.user.username
