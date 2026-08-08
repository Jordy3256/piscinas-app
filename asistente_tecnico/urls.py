from django.urls import path
from . import views

app_name = "asistente_tecnico"

urlpatterns = [
    path("", views.asistente_inicio_view, name="inicio"),
    path("historial/", views.asistente_historial_view, name="historial"),
    # Compatibilidad: la biblioteca antigua redirige conceptualmente a la biblioteca técnica nueva.
    path("biblioteca/", views.biblioteca_tecnica_view, name="biblioteca"),
    path("centro/", views.centro_conocimiento_view, name="centro_conocimiento"),
    path("academia/", views.academia_view, name="academia"),
    path("academia/leccion/<int:pk>/", views.leccion_detalle_view, name="leccion_detalle"),
    path("academia/leccion/<int:pk>/completar/", views.leccion_completar_view, name="leccion_completar"),
    path("biblioteca/articulo/<int:pk>/", views.articulo_biblioteca_detalle_view, name="biblioteca_detalle"),
    path("casos-reales/", views.casos_reales_view, name="casos_reales"),
    path("certificacion/", views.certificacion_view, name="certificacion"),
    path("casos/<int:pk>/", views.asistente_caso_detalle_view, name="caso_detalle"),
    path("casos/<int:pk>/seguimiento/", views.asistente_seguimiento_view, name="seguimiento"),
    path("administracion/", views.asistente_admin_view, name="admin"),
    path("administracion/conocimiento/", views.conocimiento_admin_view, name="conocimiento_admin"),
    path("administracion/conocimiento/motor/", views.motor_conocimiento_view, name="motor_conocimiento"),
    path("administracion/conocimiento/motor/analizar/", views.motor_conocimiento_analizar_view, name="motor_conocimiento_analizar"),
    path("administracion/conocimiento/propuesta/<int:pk>/estado/", views.propuesta_conocimiento_estado_view, name="propuesta_conocimiento_estado"),
    path("administracion/conocimiento/categoria/nueva/", views.categoria_form_view, name="categoria_nueva"),
    path("administracion/conocimiento/categoria/<int:pk>/editar/", views.categoria_form_view, name="categoria_editar"),
    path("administracion/conocimiento/leccion/nueva/", views.leccion_form_view, name="leccion_nueva"),
    path("administracion/conocimiento/leccion/<int:pk>/editar/", views.leccion_form_view, name="leccion_editar"),
    path("administracion/conocimiento/articulo/nuevo/", views.articulo_form_view, name="articulo_nuevo"),
    path("administracion/conocimiento/articulo/<int:pk>/editar/", views.articulo_form_view, name="articulo_editar"),
    path("administracion/conocimiento/consejo/nuevo/", views.consejo_form_view, name="consejo_nuevo"),
    path("administracion/conocimiento/consejo/<int:pk>/editar/", views.consejo_form_view, name="consejo_editar"),
    path("administracion/version/nueva/", views.asistente_version_nueva_view, name="version_nueva"),
    path("administracion/version/<int:pk>/activar/", views.asistente_version_activar_view, name="version_activar"),
    path("administracion/casos/<int:pk>/destacar/", views.asistente_destacar_view, name="destacar"),
]
