from django.db import models
from django.contrib.auth.models import User


class Trabajador(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    class Meta:
        verbose_name = "Trabajador"
        verbose_name_plural = "Trabajadores"
    telefono = models.CharField(max_length=20)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.user.username
