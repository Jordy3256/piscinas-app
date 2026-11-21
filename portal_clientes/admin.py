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


from django.db import transaction
from .models import ComunicadoPortal, AvisoPortal

@admin.register(ComunicadoPortal)
class ComunicadoPortalAdmin(admin.ModelAdmin):
    list_display = ('titulo','destino','publicado_en','creado_en')
    list_filter = ('destino','publicado_en')
    readonly_fields = ('publicado_en','creado_en')
    actions = ['publicar_comunicados']
    def has_add_permission(self, request): return request.user.is_superuser or request.user.has_perm('portal_clientes.add_comunicadoportal')
    @admin.action(description='Publicar comunicados seleccionados')
    def publicar_comunicados(self, request, queryset):
        from clientes.models import Cliente
        if not request.user.is_superuser and not request.user.has_perm('portal_clientes.change_comunicadoportal'):
            self.message_user(request,'Sin permisos para publicar.',messages.ERROR);return
        publicados=0
        for comunicado in queryset:
            with transaction.atomic():
                actual=ComunicadoPortal.objects.select_for_update().get(pk=comunicado.pk)
                if actual.publicado_en: continue
                clientes=Cliente.objects.filter(activo=True,acceso_portal__habilitado=True,acceso_portal__usuario__isnull=False)
                if actual.destino=='cliente': clientes=clientes.filter(pk=actual.cliente_id)
                elif actual.destino=='ciudad': clientes=clientes.filter(ciudad_ref_id=actual.ciudad_id)
                AvisoPortal.objects.bulk_create([AvisoPortal(cliente_id=cid,clave=f'comunicado:{actual.pk}',tipo='comunicado',titulo=actual.titulo,detalle=actual.contenido) for cid in clientes.values_list('pk',flat=True)],ignore_conflicts=True)
                actual.publicado_en=timezone.now();actual.save(update_fields=['publicado_en']);publicados+=1
        self.message_user(request,f'{publicados} comunicado(s) publicado(s).')
    def get_readonly_fields(self,request,obj=None):
        return ('titulo','contenido','destino','ciudad','cliente','publicado_en','creado_en') if obj and obj.publicado_en else self.readonly_fields
    def has_delete_permission(self,request,obj=None): return bool(obj is None or not obj.publicado_en) and super().has_delete_permission(request,obj)
