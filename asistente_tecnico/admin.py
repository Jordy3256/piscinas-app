from django.contrib import admin
from .models import MotorRecomendacion, CasoAsistenteTecnico, ContenidoAcademia, ImagenContenidoAcademia, VersionContenidoAcademia, ExperienciaConocimiento, PerfilSuscriptor, PiscinaSuscriptor, PlanMantenimientoPiscina, RegistroMantenimientoPiscina, SugerenciaDigital


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


@admin.register(ContenidoAcademia)
class ContenidoAcademiaAdmin(admin.ModelAdmin):
    list_display=("codigo","titulo","tipo","estado","version","actualizado_en")
    list_filter=("tipo","estado","nivel")
    search_fields=("codigo","titulo","resumen","etiquetas")

@admin.register(ExperienciaConocimiento)
class ExperienciaConocimientoAdmin(admin.ModelAdmin):
    list_display=("titulo","estado","destino_sugerido","actualizado_en")
    list_filter=("estado","destino_sugerido")
    search_fields=("titulo","problema","aprendizaje")

admin.site.register(ImagenContenidoAcademia)
admin.site.register(VersionContenidoAcademia)


@admin.register(PerfilSuscriptor)
class PerfilSuscriptorAdmin(admin.ModelAdmin):
    list_display=("user","estado","plan","inicio","prueba_hasta","acceso_hasta")
    list_filter=("estado","plan")
    search_fields=("user__username","user__first_name","user__last_name","user__email")

@admin.register(PiscinaSuscriptor)
class PiscinaSuscriptorAdmin(admin.ModelAdmin):
    list_display=("nombre","suscriptor","volumen_m3","tipo_filtro","desinfeccion","principal","activa")
    list_filter=("tipo_piscina","tipo_filtro","desinfeccion","principal","activa")
    search_fields=("nombre","suscriptor__user__username","suscriptor__user__email")


@admin.register(PlanMantenimientoPiscina)
class PlanMantenimientoPiscinaAdmin(admin.ModelAdmin):
    list_display=("piscina","frecuencia_semanal","retrolavado_dias","arena_deteriorada","activo")
    list_filter=("frecuencia_semanal","arena_deteriorada","activo")

@admin.register(RegistroMantenimientoPiscina)
class RegistroMantenimientoPiscinaAdmin(admin.ModelAdmin):
    list_display=("piscina","fecha","visita_numero","ph","cloro","completado")
    list_filter=("fecha","completado")


@admin.register(SugerenciaDigital)
class SugerenciaDigitalAdmin(admin.ModelAdmin):
    list_display = ("suscriptor", "categoria", "calificacion", "estado", "creada_en")
    list_filter = ("categoria", "calificacion", "estado", "creada_en")
    search_fields = (
        "suscriptor__user__username",
        "suscriptor__user__first_name",
        "suscriptor__user__last_name",
        "mensaje",
    )
    readonly_fields = ("creada_en", "actualizada_en")
