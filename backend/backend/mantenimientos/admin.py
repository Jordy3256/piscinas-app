from django.contrib import admin
from .models import Mantenimiento, UsoInsumo


class UsoInsumoInline(admin.TabularInline):
    model = UsoInsumo
    extra = 1


@admin.register(Mantenimiento)
class MantenimientoAdmin(admin.ModelAdmin):
    list_display = (
        'cliente',
        'fecha',
        'estado',
        'total_egresos_admin',
    )
    inlines = [UsoInsumoInline]

    def total_egresos_admin(self, obj):
        return obj.total_egresos()

    total_egresos_admin.short_description = "Total egresos"
