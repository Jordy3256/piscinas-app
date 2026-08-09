from django.contrib import admin
from .models import Contrato


@admin.register(Contrato)
class ContratoAdmin(admin.ModelAdmin):

    list_display = (
        "cliente",
        "mostrar_frecuencia",
        "mostrar_forma_pago",
        "precio_mensual",
        "fecha_inicio",
        "activo",
    )

    list_filter = (
        "frecuencia",
        "forma_pago",
        "activo",
        "fecha_inicio",
    )

    search_fields = (
        "cliente__nombre",
        "cliente__telefono",
        "frecuencia_personalizada",
        "forma_pago_personalizada",
    )

    ordering = (
        "-activo",
        "cliente__nombre",
    )

    list_select_related = (
        "cliente",
    )

    fieldsets = (
        (
            "Información del cliente",
            {
                "fields": (
                    "cliente",
                    "activo",
                )
            },
        ),
        (
            "Servicio contratado",
            {
                "fields": (
                    "frecuencia",
                    "frecuencia_personalizada",
                    "tipo",
                ),
                "description": (
                    "El campo «tipo» se mantiene temporalmente para "
                    "compatibilidad con los contratos anteriores."
                ),
            },
        ),
        (
            "Gestión de químicos",
            {
                "fields": (
                    "quimicos_proveedor",
                    "quimicos_almacenamiento",
                    "responsable_reposicion",
                )
            },
        ),
        (
            "Información de pago",
            {
                "fields": (
                    "precio_mensual",
                    "forma_pago",
                    "forma_pago_personalizada",
                    "fecha_inicio",
                )
            },
        ),
    )

    @admin.display(
        description="Frecuencia",
        ordering="frecuencia",
    )
    def mostrar_frecuencia(self, obj):
        return obj.frecuencia_completa()

    @admin.display(
        description="Forma de pago",
        ordering="forma_pago",
    )
    def mostrar_forma_pago(self, obj):
        return obj.forma_pago_completa()