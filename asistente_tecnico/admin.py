from django.contrib import admin
from .models import MotorRecomendacion, CasoAsistenteTecnico


@admin.register(MotorRecomendacion)
class MotorRecomendacionAdmin(admin.ModelAdmin):
    list_display = ("version", "nombre", "activo", "creado_en")
    list_filter = ("activo",)
    search_fields = ("version", "nombre", "descripcion")


@admin.register(CasoAsistenteTecnico)
class CasoAsistenteTecnicoAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "tipo_tratamiento", "estado_agua", "resultado", "destacado", "creado_en")
    list_filter = ("tipo_tratamiento", "estado_agua", "tipo_piscina", "resultado", "destacado")
    search_fields = ("user__username", "user__first_name", "user__last_name", "diagnostico")
