from django.conf import settings
from django.db import models
from django.utils import timezone

class AccesoCliente(models.Model):
    cliente = models.OneToOneField('clientes.Cliente', on_delete=models.PROTECT, related_name='acceso_portal')
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name='acceso_cliente_jvaqua')
    codigo_hash = models.CharField(max_length=128, blank=True)
    codigo_expira = models.DateTimeField(null=True, blank=True)
    activado_en = models.DateTimeField(null=True, blank=True)
    habilitado = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    def codigo_valido(self):
        return bool(self.codigo_hash and self.codigo_expira and self.codigo_expira > timezone.now() and not self.usuario_id and self.habilitado)

    def __str__(self):
        return f'Portal: {self.cliente}'
