from django.contrib import admin
from .models import Contrato


@admin.register(Contrato)
class ContratoAdmin(admin.ModelAdmin):

    list_display = ('cliente', 'tipo', 'precio_mensual', 'activo')
    list_filter = ('tipo', 'activo')
    search_fields = ('cliente__nombre',)