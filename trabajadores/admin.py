from django.contrib import admin
from .models import Trabajador

@admin.register(Trabajador)
class TrabajadorAdmin(admin.ModelAdmin):
    list_display = ('user', 'activo', 'forma_pago_nomina', 'programacion_pago_nomina', 'modalidad_pago_nomina')
    list_filter = ('activo', 'forma_pago_nomina', 'programacion_pago_nomina')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'telefono')
