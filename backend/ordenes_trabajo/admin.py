from django.contrib import admin
from .models import OrdenTrabajo, FotoOrdenTrabajo, TipoOrdenTrabajo


@admin.register(TipoOrdenTrabajo)
class TipoOrdenTrabajoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "icono", "color", "activo", "orden")
    list_editable = ("activo", "orden")


@admin.register(OrdenTrabajo)
class OrdenTrabajoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre_contacto", "tipo", "fecha", "trabajador", "estado", "origen")
    list_filter = ("estado", "origen", "tipo", "fecha")
    search_fields = ("nombre_contacto", "telefono", "titulo", "direccion")


@admin.register(FotoOrdenTrabajo)
class FotoOrdenTrabajoAdmin(admin.ModelAdmin):
    list_display = ("orden", "tipo", "creada_en")
