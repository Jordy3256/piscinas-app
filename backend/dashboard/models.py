from django.db import models
from django.contrib.auth.models import User


class PushSubscription(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="push_subscriptions",
    )

    endpoint = models.TextField(unique=True)
    p256dh = models.TextField()
    auth = models.TextField()

    user_agent = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-created_at"]
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["updated_at"]),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.created_at:%Y-%m-%d %H:%M}"


class Notificacion(models.Model):
    TIPO_CHOICES = [
        ("general", "General"),
        ("mantenimiento_hoy", "Mantenimiento hoy"),
        ("mantenimiento_manana", "Mantenimiento mañana"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notificaciones",
    )

    titulo = models.CharField(max_length=150)
    mensaje = models.TextField()
    url = models.CharField(max_length=255, blank=True, default="")

    tipo = models.CharField(
        max_length=50,
        choices=TIPO_CHOICES,
        default="general",
    )

    referencia_id = models.IntegerField(
        blank=True,
        null=True,
        help_text="ID del objeto relacionado (ej: mantenimiento)",
    )

    leida = models.BooleanField(default=False)
    creada_en = models.DateTimeField(auto_now_add=True)
    leida_en = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-creada_en"]
        indexes = [
            models.Index(fields=["user", "leida"]),
            models.Index(fields=["user", "creada_en"]),
            models.Index(fields=["creada_en"]),
            models.Index(fields=["tipo"]),
            models.Index(fields=["referencia_id"]),
        ]
        unique_together = [
            ("user", "tipo", "referencia_id")
        ]

    def __str__(self):
        estado = "leída" if self.leida else "no leída"
        return f"{self.user.username} | {self.titulo} | {estado}"


class ActividadSistema(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="actividades_sistema",
    )
    titulo = models.CharField(max_length=150)
    descripcion = models.TextField()
    url = models.CharField(max_length=255, blank=True, default="")
    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-creada_en"]
        indexes = [
            models.Index(fields=["creada_en"]),
            models.Index(fields=["user", "creada_en"]),
        ]

    def __str__(self):
        actor = self.user.username if self.user else "Sistema"
        return f"{actor} | {self.titulo} | {self.creada_en:%Y-%m-%d %H:%M}"