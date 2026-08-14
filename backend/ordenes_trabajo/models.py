from io import BytesIO
from decimal import Decimal

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import models
from PIL import Image

from clientes.models import Cliente
from contratos.models import Contrato
from trabajadores.models import Trabajador


class TipoOrdenTrabajo(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    icono = models.CharField(max_length=20, blank=True, default="🛠")
    color = models.CharField(max_length=20, blank=True, default="primary")
    activo = models.BooleanField(default=True)
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["orden", "nombre"]
        verbose_name = "Tipo de orden de trabajo"
        verbose_name_plural = "Tipos de órdenes de trabajo"

    def __str__(self):
        return self.nombre


class OrdenTrabajo(models.Model):
    ORIGEN_CHOICES = [
        ("contrato", "Cliente con contrato"),
        ("puntual", "Cliente / visita puntual"),
    ]
    ESTADO_CHOICES = [
        ("pendiente", "Pendiente"),
        ("en_proceso", "En proceso"),
        ("completada", "Completada"),
        ("cancelada", "Cancelada"),
    ]

    origen = models.CharField(max_length=20, choices=ORIGEN_CHOICES, default="puntual")
    tipo = models.ForeignKey(TipoOrdenTrabajo, on_delete=models.PROTECT, related_name="ordenes")

    cliente = models.ForeignKey(Cliente, on_delete=models.SET_NULL, null=True, blank=True, related_name="ordenes_trabajo")
    contrato = models.ForeignKey(Contrato, on_delete=models.SET_NULL, null=True, blank=True, related_name="ordenes_trabajo")

    # Datos operativos congelados para que la orden conserve la información usada ese día.
    nombre_contacto = models.CharField(max_length=150)
    telefono = models.CharField(max_length=50, blank=True, default="")
    ciudad = models.CharField(max_length=100, blank=True, default="")
    sector_urbanizacion = models.CharField(max_length=150, blank=True, default="")
    direccion = models.TextField(blank=True, default="")
    enlace_google_maps = models.URLField(max_length=500, blank=True, default="")

    fecha = models.DateField(db_index=True)
    hora = models.TimeField(null=True, blank=True)
    trabajador = models.ForeignKey(Trabajador, on_delete=models.PROTECT, related_name="ordenes_trabajo")
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default="pendiente", db_index=True)

    titulo = models.CharField(max_length=160, blank=True, default="")
    observaciones_admin = models.TextField(blank=True, default="")
    reporte_trabajador = models.TextField(blank=True, default="")

    valor_cliente = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    pago_trabajador = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    cortesia = models.BooleanField(default=False, help_text="Orden sin cobro adicional al cliente.")

    creada_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="ordenes_trabajo_creadas")
    creada_en = models.DateTimeField(auto_now_add=True)
    actualizada_en = models.DateTimeField(auto_now=True)
    iniciada_en = models.DateTimeField(null=True, blank=True)
    completada_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["fecha", "hora", "id"]
        verbose_name = "Orden de trabajo"
        verbose_name_plural = "Órdenes de trabajo"
        indexes = [
            models.Index(fields=["fecha", "estado"]),
            models.Index(fields=["trabajador", "fecha"]),
        ]

    def __str__(self):
        return f"OT-{self.pk or 'NUEVA'} · {self.nombre_contacto} · {self.fecha}"

    @property
    def codigo(self):
        return f"OT-{self.pk:06d}" if self.pk else "OT-NUEVA"

    @property
    def descripcion_corta(self):
        return self.titulo or (self.tipo.nombre if self.tipo_id else "Orden de trabajo")

    @property
    def es_facturable(self):
        return not self.cortesia and self.valor_cliente is not None and self.valor_cliente > Decimal("0")

    def sincronizar_desde_contrato(self):
        if not self.contrato_id:
            return
        self.origen = "contrato"
        self.cliente = self.contrato.cliente
        c = self.contrato.cliente
        self.nombre_contacto = c.nombre
        self.telefono = c.telefono or ""
        self.ciudad = c.ciudad or ""
        self.sector_urbanizacion = c.sector_urbanizacion or ""
        self.direccion = c.direccion or ""
        self.enlace_google_maps = c.enlace_google_maps or ""
        if not self.trabajador_id and self.contrato.tecnico_designado_id:
            self.trabajador = self.contrato.tecnico_designado


class FotoOrdenTrabajo(models.Model):
    TIPO_CHOICES = [
        ("antes", "Antes"),
        ("durante", "Durante"),
        ("despues", "Después"),
        ("otro", "Otro"),
    ]
    orden = models.ForeignKey(OrdenTrabajo, on_delete=models.CASCADE, related_name="fotos")
    imagen = models.ImageField(upload_to="ordenes_trabajo/")
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default="otro")
    descripcion = models.CharField(max_length=180, blank=True, default="")
    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["creada_en", "id"]

    def save(self, *args, **kwargs):
        nueva = bool(self.imagen) and not self.pk
        if nueva:
            try:
                img = Image.open(self.imagen)
                if img.mode != "RGB":
                    img = img.convert("RGB")
                img.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
                buffer = BytesIO()
                img.save(buffer, format="JPEG", quality=80, optimize=True)
                buffer.seek(0)
                nombre = self.imagen.name.rsplit(".", 1)[0] + ".jpg"
                self.imagen.save(nombre, ContentFile(buffer.read()), save=False)
            except Exception:
                pass
        super().save(*args, **kwargs)
