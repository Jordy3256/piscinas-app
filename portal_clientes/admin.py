import secrets
from datetime import timedelta
from django.contrib import admin, messages
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from .models import AccesoCliente

@admin.register(AccesoCliente)
class AccesoClienteAdmin(admin.ModelAdmin):
    list_display = ('cliente', 'habilitado', 'activado_en', 'codigo_expira')
    search_fields = ('cliente__nombre', 'cliente__email')
    readonly_fields = ('usuario', 'activado_en', 'codigo_hash', 'codigo_expira', 'creado_en')
    actions = ['generar_codigo']

    @admin.action(description='Generar código de activación (solo cuentas sin activar)')
    def generar_codigo(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(request, 'Seleccione exactamente un cliente por vez.', messages.ERROR)
            return
        acceso = queryset.select_related('cliente').first()
        if acceso.usuario_id or not acceso.habilitado or not acceso.cliente.activo or not acceso.cliente.email:
            self.message_user(request, 'Cliente no apto para activar.', messages.ERROR)
            return
        email = acceso.cliente.email.strip()
        from clientes.models import Cliente
        if Cliente.objects.filter(email__iexact=email).exclude(pk=acceso.cliente_id).exists():
            self.message_user(request, 'Correo duplicado: resuelva la identidad antes de generar código.', messages.ERROR)
            return
        codigo = secrets.token_urlsafe(24)
        acceso.codigo_hash = make_password(codigo)
        acceso.codigo_expira = timezone.now() + timedelta(hours=48)
        acceso.save(update_fields=['codigo_hash','codigo_expira'])
        self.message_user(request, f'CÓDIGO DE UN SOLO USO (visible únicamente ahora): {codigo}. Entregar al cliente por canal verificado; vence en 48 horas.', messages.WARNING)
