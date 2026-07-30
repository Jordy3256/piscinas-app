from django.contrib import admin

from .models import Egreso, Factura, FacturaItem, Ingreso, MovimientoRecurrente, PagoFactura


@admin.register(Ingreso)
class IngresoAdmin(admin.ModelAdmin):
    list_display = ("fecha", "concepto", "total", "monto_pagado", "estado", "cliente", "metodo_pago")
    list_filter = ("estado", "metodo_pago", "fecha")
    search_fields = ("concepto", "cliente__nombre", "ciudad")
    readonly_fields = ("creado_en", "actualizado_en")


@admin.register(Egreso)
class EgresoAdmin(admin.ModelAdmin):
    list_display = ("fecha", "concepto", "categoria", "total", "monto_pagado", "estado", "aprobado")
    list_filter = ("categoria", "estado", "aprobado", "fecha")
    search_fields = ("concepto", "proveedor", "ciudad_proyecto")
    readonly_fields = ("total", "creado_en", "actualizado_en")


@admin.register(MovimientoRecurrente)
class MovimientoRecurrenteAdmin(admin.ModelAdmin):
    list_display = ("tipo", "concepto", "monto", "frecuencia", "proxima_fecha", "activo")
    list_filter = ("tipo", "frecuencia", "activo")
    search_fields = ("concepto",)


class FacturaItemInline(admin.TabularInline):
    model = FacturaItem
    extra = 0


@admin.register(Factura)
class FacturaAdmin(admin.ModelAdmin):
    list_display = ("numero", "cliente", "periodo_label", "total", "estado", "fecha_vencimiento")
    list_filter = ("estado", "periodo_anio", "periodo_mes")
    search_fields = ("numero", "cliente__nombre")
    inlines = [FacturaItemInline]


@admin.register(PagoFactura)
class PagoFacturaAdmin(admin.ModelAdmin):
    list_display = ("fecha", "factura", "monto", "metodo_pago", "activo")
    list_filter = ("activo", "metodo_pago", "fecha")
    search_fields = ("factura__numero", "factura__cliente__nombre", "referencia")
    readonly_fields = ("ingreso", "creado_en", "actualizado_en")

from .models import ObligacionTrabajador, PagoTrabajador


@admin.register(ObligacionTrabajador)
class ObligacionTrabajadorAdmin(admin.ModelAdmin):
    list_display = ("trabajador", "contrato", "periodo_label", "fecha_pago_programada", "valor_acordado", "estado")
    list_filter = ("estado", "periodo_anio", "periodo_mes", "fecha_pago_programada")
    search_fields = ("trabajador__user__username", "trabajador__user__first_name", "trabajador__user__last_name", "contrato__cliente__nombre")


@admin.register(PagoTrabajador)
class PagoTrabajadorAdmin(admin.ModelAdmin):
    list_display = ("fecha", "obligacion", "monto", "metodo_pago", "activo")
    list_filter = ("activo", "metodo_pago", "fecha")
    search_fields = ("obligacion__contrato__cliente__nombre", "obligacion__trabajador__user__username", "referencia")
    readonly_fields = ("egreso", "creado_en", "actualizado_en")
