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


class ConversacionSoporte(models.Model):
    cliente = models.ForeignKey('clientes.Cliente', on_delete=models.PROTECT, related_name='conversaciones_soporte')
    contrato = models.ForeignKey('contratos.Contrato', on_delete=models.PROTECT, null=True, blank=True, related_name='conversaciones_soporte')
    creada_en = models.DateTimeField(auto_now_add=True)
    actualizada_en = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ['-actualizada_en', '-pk']

    def __str__(self):
        return f'Soporte #{self.pk} - {self.cliente}'


class MensajeSoporte(models.Model):
    conversacion = models.ForeignKey(ConversacionSoporte, on_delete=models.CASCADE, related_name='mensajes')
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    es_cliente = models.BooleanField()
    contenido = models.TextField(max_length=2000, blank=True)
    archivo = models.BinaryField(null=True, blank=True, editable=False)
    archivo_tipo = models.CharField(max_length=80, blank=True)
    archivo_nombre = models.CharField(max_length=120, blank=True)
    archivo_clase = models.CharField(max_length=12, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    leido_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['creado_en', 'pk']


class NotificacionMantenimientoCliente(models.Model):
    """Aviso persistente y privado, derivado de un mantenimiento real."""
    TIPO_PROXIMA = 'proxima'
    TIPO_REALIZADO = 'realizado'
    TIPO_REPORTE = 'reporte'
    cliente = models.ForeignKey('clientes.Cliente', on_delete=models.CASCADE, related_name='avisos_portal')
    mantenimiento = models.ForeignKey('mantenimientos.Mantenimiento', on_delete=models.CASCADE, related_name='avisos_portal')
    tipo = models.CharField(max_length=12)
    creada_en = models.DateTimeField(default=timezone.now)
    leida_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['cliente', 'mantenimiento', 'tipo'], name='portal_aviso_mantenimiento_unico')]
        ordering = ['-creada_en', '-pk']
