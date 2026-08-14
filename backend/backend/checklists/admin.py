from django.contrib import admin
from .models import ChecklistItem


@admin.register(ChecklistItem)
class ChecklistItemAdmin(admin.ModelAdmin):
    list_display = ('descripcion', 'mantenimiento', 'realizado')
    list_filter = ('realizado',)
    search_fields = ('descripcion',)
from .models import ChecklistPlantilla


@admin.register(ChecklistPlantilla)
class ChecklistPlantillaAdmin(admin.ModelAdmin):
    list_display = ('contrato', 'descripcion')
    search_fields = ('descripcion',)
