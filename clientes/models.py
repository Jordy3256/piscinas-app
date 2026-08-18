from django.db import models


class Ciudad(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    activa = models.BooleanField(default=True)
    orden = models.PositiveSmallIntegerField(default=0)

    def save(self, *args, **kwargs):
        self.nombre = (self.nombre or "").strip().title()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre

    class Meta:
        ordering = ["orden", "nombre"]
        verbose_name = "Ciudad"
        verbose_name_plural = "Ciudades"


class Cliente(models.Model):
    nombre = models.CharField(max_length=150)
    telefono = models.CharField(max_length=50)
    email = models.EmailField(blank=True, null=True)
    ciudad = models.CharField(max_length=100, blank=True, default="")
    ciudad_ref = models.ForeignKey(Ciudad, on_delete=models.SET_NULL, null=True, blank=True, related_name="clientes")
    sector_urbanizacion = models.CharField(max_length=150, blank=True, default="")
    direccion = models.TextField()
    enlace_google_maps = models.URLField(max_length=500, blank=True, default="")
    latitud = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitud = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    activo = models.BooleanField(default=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        self.nombre = (self.nombre or "").strip()
        self.telefono = (self.telefono or "").strip()
        self.email = (self.email or "").strip() or None
        self.ciudad = (self.ciudad or "").strip()
        if self.ciudad_ref_id:
            self.ciudad = self.ciudad_ref.nombre
        elif self.ciudad:
            ciudad_obj, _ = Ciudad.objects.get_or_create(nombre__iexact=self.ciudad, defaults={"nombre": self.ciudad})
            self.ciudad_ref = ciudad_obj
            self.ciudad = ciudad_obj.nombre
        self.sector_urbanizacion = (self.sector_urbanizacion or "").strip()
        self.direccion = (self.direccion or "").strip()
        self.enlace_google_maps = (self.enlace_google_maps or "").strip()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre

    class Meta:
        ordering = ["nombre", "id"]
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
