from django.contrib import admin

from .models import (
    CompraInsumo,
    EntradaStock,
    Insumo,
    InventarioTrabajador,
    MovimientoInventario,
    PresentacionInsumo,
    VentaInsumo,
)


class PresentacionInline(admin.TabularInline):
    model = PresentacionInsumo
    extra = 0


@admin.register(Insumo)
class InsumoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "categoria", "stock", "unidad_base", "stock_minimo", "estado_stock", "costo", "precio")
    list_filter = ("categoria", "unidad_base", "activo", "puede_mantenimiento", "puede_venderse")
    search_fields = ("nombre", "codigo")
    inlines = [PresentacionInline]

    def estado_stock(self, obj):
        if obj.stock <= 0:
            return "⛔ Sin stock"
        if obj.stock <= obj.stock_minimo:
            return "⚠ Bajo stock"
        return "✔ OK"

    estado_stock.short_description = "Estado"


@admin.register(InventarioTrabajador)
class InventarioTrabajadorAdmin(admin.ModelAdmin):
    list_display = ("trabajador", "insumo", "stock", "actualizado_en")
    list_filter = ("trabajador", "insumo__categoria")
    search_fields = ("trabajador__user__username", "insumo__nombre")


@admin.register(MovimientoInventario)
class MovimientoInventarioAdmin(admin.ModelAdmin):
    list_display = ("fecha", "tipo", "insumo", "cantidad", "trabajador", "mantenimiento")
    list_filter = ("tipo", "fecha", "insumo__categoria", "trabajador")
    search_fields = ("insumo__nombre", "trabajador__user__username", "observacion")


admin.site.register(CompraInsumo)
admin.site.register(VentaInsumo)
admin.site.register(EntradaStock)
