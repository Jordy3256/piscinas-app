from django.urls import path
from . import views

app_name = "asistente_tecnico"

urlpatterns = [
    path("", views.asistente_inicio_view, name="inicio"),
    path("historial/", views.asistente_historial_view, name="historial"),
    path("biblioteca/", views.asistente_biblioteca_view, name="biblioteca"),
    path("casos/<int:pk>/", views.asistente_caso_detalle_view, name="caso_detalle"),
    path("casos/<int:pk>/seguimiento/", views.asistente_seguimiento_view, name="seguimiento"),
    path("administracion/", views.asistente_admin_view, name="admin"),
    path("administracion/version/nueva/", views.asistente_version_nueva_view, name="version_nueva"),
    path("administracion/version/<int:pk>/activar/", views.asistente_version_activar_view, name="version_activar"),
    path("administracion/casos/<int:pk>/destacar/", views.asistente_destacar_view, name="destacar"),
]
