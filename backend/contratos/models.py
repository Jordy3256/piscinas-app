from django.db import models

from clientes.models import Cliente


class Contrato(models.Model):

    # Campo anterior conservado para no afectar
    # mantenimientos, facturación ni registros existentes.
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
        ("50_50", "50/50"),
        ("por_visita", "Por visita"),
        ("fin_mensualidad", "Fin de la mensualidad"),
        ("personalizado", "Personalizado"),
    ]

    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.CASCADE,
        related_name="contratos",
    )

    # Campo anterior.
    # Se conserva temporalmente para compatibilidad.
    tipo = models.CharField(
        max_length=20,
        choices=TIPO_CHOICES,
    )

    frecuencia = models.CharField(
        max_length=30,
        choices=FRECUENCIA_CHOICES,
        blank=True,
        default="",
    )

    frecuencia_personalizada = models.CharField(
        max_length=150,
        blank=True,
        default="",
        help_text="Completar únicamente cuando la frecuencia sea personalizada.",
    )

    forma_pago = models.CharField(
        max_length=30,
        choices=FORMA_PAGO_CHOICES,
        blank=True,
        default="",
    )

    forma_pago_personalizada = models.CharField(
        max_length=150,
        blank=True,
        default="",
        help_text="Completar únicamente cuando la forma de pago sea personalizada.",
    )

    precio_mensual = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    fecha_inicio = models.DateField()

    activo = models.BooleanField(
        default=True,
    )

    def ingreso_mensual(self):
        return self.precio_mensual

    def frecuencia_completa(self):
        """
        Devuelve la frecuencia lista para mostrar.

        Los contratos antiguos que todavía no tengan el nuevo campo
        utilizarán temporalmente el valor del campo tipo.
        """
        if self.frecuencia == "personalizado":
            return self.frecuencia_personalizada or "Personalizada"

        if self.frecuencia:
            return self.get_frecuencia_display()

        # Compatibilidad con contratos anteriores.
        equivalencias = {
            "semanal": "Semanal",
            "quincenal": "Cada 15 días",
            "mensual": "Mensual",
            "variable": "Variable",
        }

        return equivalencias.get(self.tipo, self.tipo or "Sin definir")

    frecuencia_completa.short_description = "Frecuencia"

    def forma_pago_completa(self):
        """
        Devuelve la forma de pago lista para mostrar.
        """
        if self.forma_pago == "personalizado":
            return self.forma_pago_personalizada or "Personalizada"

        if self.forma_pago:
            return self.get_forma_pago_display()

        return "Sin definir"

    forma_pago_completa.short_description = "Forma de pago"

    def sincronizar_tipo_compatibilidad(self):
        """
        Mantiene actualizado el campo anterior tipo para evitar
        incompatibilidades con otras partes del sistema.
        """
        equivalencias = {
            "1_semanal": "semanal",
            "2_semanales": "semanal",
            "3_semanales": "semanal",
            "quincenal": "quincenal",
            "personalizado": "variable",
        }

        if self.frecuencia in equivalencias:
            self.tipo = equivalencias[self.frecuencia]

    def save(self, *args, **kwargs):
        self.frecuencia_personalizada = (
            self.frecuencia_personalizada or ""
        ).strip()

        self.forma_pago_personalizada = (
            self.forma_pago_personalizada or ""
        ).strip()

        if self.frecuencia != "personalizado":
            self.frecuencia_personalizada = ""

        if self.forma_pago != "personalizado":
            self.forma_pago_personalizada = ""

        self.sincronizar_tipo_compatibilidad()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.cliente} - {self.frecuencia_completa()}"

    class Meta:
        verbose_name = "Contrato"
        verbose_name_plural = "Contratos"
        ordering = ["-activo", "cliente__nombre", "id"]