from io import BytesIO

from django.core.files.base import ContentFile
from django.db import models
from PIL import Image

from clientes.models import Cliente
from contratos.models import Contrato
from inventario.models import Insumo
from trabajadores.models import Trabajador


class Mantenimiento(models.Model):
    ESTADO_CHOICES = [
        ("pendiente", "Pendiente"),
        ("realizado", "Realizado"),
    ]

    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.CASCADE,
    )
    contrato = models.ForeignKey(
        Contrato,
        on_delete=models.CASCADE,
    )
    fecha = models.DateField()
    trabajadores = models.ManyToManyField(Trabajador)
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default="pendiente",
    )
    automatico = models.BooleanField(
        default=False,
        help_text="Indica si fue generado desde la programación automática del contrato.",
    )
    observaciones = models.TextField(blank=True)

    ESTADO_AGUA_RAPIDO = [
        ("", "Sin seleccionar"),
        ("cristalina", "Agua cristalina"),
        ("turbidez", "Ligera turbidez"),
        ("verde", "Agua verde"),
    ]
    EQUIPO_RAPIDO = [
        ("", "Sin seleccionar"),
        ("correcto", "Todo funcionando correctamente"),
        ("bomba_ruido", "Bomba con ruido"),
        ("filtro_revision", "Filtro requiere revisión"),
    ]
    estado_agua_rapido = models.CharField(max_length=20, choices=ESTADO_AGUA_RAPIDO, blank=True, default="")
    equipo_rapido = models.CharField(max_length=30, choices=EQUIPO_RAPIDO, blank=True, default="")
    recomendaciones_rapidas = models.JSONField(default=list, blank=True)
    borrador_guardado = models.BooleanField(default=False)

    def total_egresos(self):
        total = 0

        for uso in self.usos_insumos.all():
            total += uso.subtotal()

        return total

    total_egresos.short_description = "Total egresos"

    def __str__(self):
        return f"{self.cliente} - {self.fecha}"

    class Meta:
        verbose_name = "Mantenimiento"
        verbose_name_plural = "Mantenimientos"


class UsoInsumo(models.Model):
    UNIDAD_REGISTRO_CHOICES = [
        ("g", "Gramos"),
        ("kg", "Kilogramos"),
        ("unidad", "Unidades"),
    ]

    mantenimiento = models.ForeignKey(
        "mantenimientos.Mantenimiento",
        on_delete=models.CASCADE,
        related_name="usos_insumos",
    )
    insumo = models.ForeignKey(
        Insumo,
        on_delete=models.PROTECT,
    )
    trabajador = models.ForeignKey(
        Trabajador,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="usos_insumos",
    )
    cantidad = models.DecimalField(max_digits=12, decimal_places=3, help_text="Cantidad convertida a la unidad base del producto.")
    cantidad_ingresada = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    unidad_registro = models.CharField(max_length=10, choices=UNIDAD_REGISTRO_CHOICES, default="kg")
    costo_unitario = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    costo_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Se conserva para compatibilidad con consumos históricos que generaban un Egreso.
    # Los consumos nuevos no crean egreso porque el costo ya se reconoce al comprar inventario.
    egreso = models.OneToOneField(
        "finanzas.Egreso",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uso_insumo",
    )

    def subtotal(self):
        if self.costo_total:
            return self.costo_total
        return (self.insumo.costo or 0) * self.cantidad

    @property
    def cantidad_mostrada(self):
        if self.cantidad_ingresada is not None:
            return self.cantidad_ingresada
        if self.insumo.unidad_base == "kg" and self.cantidad < 1:
            return self.cantidad * 1000
        return self.cantidad

    @property
    def unidad_mostrada(self):
        if self.cantidad_ingresada is not None:
            return self.unidad_registro
        if self.insumo.unidad_base == "kg" and self.cantidad < 1:
            return "g"
        return self.insumo.unidad_base

    def __str__(self):
        return f"{self.insumo.nombre} - {self.cantidad_mostrada} {self.unidad_mostrada}"


class FotoMantenimiento(models.Model):
    mantenimiento = models.ForeignKey(
        "mantenimientos.Mantenimiento",
        on_delete=models.CASCADE,
        related_name="fotos",
    )
    imagen = models.ImageField(
        upload_to="mantenimientos/",
    )
    descripcion = models.CharField(
        max_length=200,
        blank=True,
    )
    creada_en = models.DateTimeField(
        auto_now_add=True,
    )

    def save(self, *args, **kwargs):
        nueva = False

        if self.imagen:
            if not self.pk:
                nueva = True
            else:
                try:
                    anterior = FotoMantenimiento.objects.get(pk=self.pk)

                    if anterior.imagen != self.imagen:
                        nueva = True
                except FotoMantenimiento.DoesNotExist:
                    nueva = True

        if nueva:
            try:
                img = Image.open(self.imagen)

                if img.mode != "RGB":
                    img = img.convert("RGB")

                img.thumbnail(
                    (1400, 1400),
                    Image.Resampling.LANCZOS,
                )

                buffer = BytesIO()

                img.save(
                    buffer,
                    format="JPEG",
                    quality=78,
                    optimize=True,
                )

                buffer.seek(0)

                nombre = self.imagen.name.rsplit(".", 1)[0] + ".jpg"

                self.imagen.save(
                    nombre,
                    ContentFile(buffer.read()),
                    save=False,
                )
            except Exception:
                pass

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Foto #{self.id} - {self.mantenimiento}"


class ChecklistMantenimiento(models.Model):
    ESTADO_EQUIPO = [
        ("correcto", "Funciona correctamente"),
        ("novedad", "Presenta novedad"),
    ]

    NIVEL_AGUA = [
        ("bajo", "Bajo"),
        ("alto", "Alto"),
        ("normal", "Normal"),
    ]

    mantenimiento = models.OneToOneField(
        Mantenimiento,
        on_delete=models.CASCADE,
        related_name="checklist_v2",
    )

    aspirado = models.BooleanField(default=False)
    cepillado = models.BooleanField(default=False)
    recoleccion_basura = models.BooleanField(default=False)
    limpieza_filtros = models.BooleanField(default=False)
    retrolavado_arena = models.BooleanField(default=False)
    limpieza_filos = models.BooleanField(default=False)

    cloro_granulado = models.BooleanField(default=False)
    tricloro = models.BooleanField(default=False)
    alguicida = models.BooleanField(default=False)
    metasilicato = models.BooleanField(default=False)
    floculante = models.BooleanField(default=False)

    bomba_estado = models.CharField(
        max_length=20,
        choices=ESTADO_EQUIPO,
        blank=True,
    )
    bomba_novedad = models.TextField(blank=True)

    filtro_estado = models.CharField(
        max_length=20,
        choices=ESTADO_EQUIPO,
        blank=True,
    )
    filtro_novedad = models.TextField(blank=True)

    nivel_agua = models.CharField(
        max_length=20,
        choices=NIVEL_AGUA,
        blank=True,
    )

    actualizado_en = models.DateTimeField(auto_now=True)

    def completo(self):
        limpieza = all(
            [
                self.aspirado,
                self.cepillado,
                self.recoleccion_basura,
                self.limpieza_filtros,
                self.retrolavado_arena,
            ]
        )

        inspeccion = bool(
            self.bomba_estado
            and self.filtro_estado
            and self.nivel_agua
        )

        bomba_completa = not (
            self.bomba_estado == "novedad"
            and not self.bomba_novedad.strip()
        )

        filtro_completo = not (
            self.filtro_estado == "novedad"
            and not self.filtro_novedad.strip()
        )

        return (
            limpieza
            and inspeccion
            and bomba_completa
            and filtro_completo
        )

    def __str__(self):
        return f"Checklist - {self.mantenimiento}"