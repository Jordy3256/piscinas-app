from django.contrib import admin
from .models import Insumo

@admin.register(Insumo)
class InsumoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'stock', 'stock_minimo', 'estado_stock')

    def estado_stock(self, obj):
        if obj.stock <= obj.stock_minimo:
            return "⚠ Bajo stock"
        return "✔ OK"

    estado_stock.short_description = "Estado"
