from django.contrib import admin
from .models import Cliente


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("nombre", "telefono", "ciudad", "sector_urbanizacion", "email", "activo")
    search_fields = ("nombre", "telefono", "email", "ciudad", "sector_urbanizacion")
    list_filter = ("activo", "ciudad")
