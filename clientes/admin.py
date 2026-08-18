from django.contrib import admin
from .models import Cliente, Ciudad


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("nombre", "telefono", "ciudad", "sector_urbanizacion", "gps_estado", "email", "activo")
    search_fields = ("nombre", "telefono", "email", "ciudad", "sector_urbanizacion", "direccion")
    list_filter = ("activo", "ciudad")
    fieldsets = (
        ("Cliente", {"fields": ("nombre", "telefono", "email", "ciudad", "sector_urbanizacion", "direccion", "enlace_google_maps", "activo")}),
        ("GPS preciso para rutas", {"fields": ("latitud", "longitud"), "description": "Opcional. Si se ingresan coordenadas manuales, tienen prioridad sobre el enlace y la dirección."}),
    )

    @admin.display(description="GPS")
    def gps_estado(self, obj):
        return "✓ Verificado" if obj.latitud is not None and obj.longitud is not None else "⚠ Pendiente"

admin.site.register(Ciudad)
