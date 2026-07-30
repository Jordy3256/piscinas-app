from django.contrib import admin
from .models import Egreso, Ingreso, MovimientoRecurrente


@admin.register(Ingreso)
class IngresoAdmin(admin.ModelAdmin):
    list_display = ("fecha", "concepto", "total", "cliente", "contrato")
    list_filter = ("fecha",)
    search_fields = ("concepto", "cliente__nombre")


@admin.register(MovimientoRecurrente)
class MovimientoRecurrenteAdmin(admin.ModelAdmin):
    list_display = ("tipo", "concepto", "monto", "frecuencia", "proxima_fecha", "activo")
    list_filter = ("tipo", "frecuencia", "activo")
    search_fields = ("concepto",)


@admin.register(Egreso)
class EgresoAdmin(admin.ModelAdmin):
    list_display = ("fecha", "insumo", "cantidad", "costo_unitario", "total")
    list_filter = ("fecha",)
