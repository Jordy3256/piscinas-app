from django.db import models


class Cliente(models.Model):
    nombre = models.CharField(max_length=150)
    telefono = models.CharField(max_length=50)
    email = models.EmailField(blank=True, null=True)
    ciudad = models.CharField(max_length=100, blank=True, default="")
    sector_urbanizacion = models.CharField(max_length=150, blank=True, default="")
    direccion = models.TextField()
    enlace_google_maps = models.URLField(max_length=500, blank=True, default="")
    activo = models.BooleanField(default=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        self.nombre = (self.nombre or "").strip()
        self.telefono = (self.telefono or "").strip()
        self.email = (self.email or "").strip() or None
        self.ciudad = (self.ciudad or "").strip()
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
