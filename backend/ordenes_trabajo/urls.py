from django.urls import path
from . import views

app_name = "ordenes_trabajo"

urlpatterns = [
    path("", views.orden_list_view, name="lista"),
    path("nueva/", views.orden_crear_view, name="crear"),
    path("nueva/contrato/<int:contrato_id>/", views.orden_crear_view, name="crear_desde_contrato"),
    path("mis-ordenes/", views.mis_ordenes_view, name="mis_ordenes"),
    path("<int:pk>/", views.orden_detalle_view, name="detalle"),
    path("<int:pk>/editar/", views.orden_editar_view, name="editar"),
    path("<int:pk>/iniciar/", views.orden_iniciar_view, name="iniciar"),
    path("<int:pk>/guardar/", views.orden_guardar_trabajador_view, name="guardar_trabajador"),
    path("<int:pk>/cancelar/", views.orden_cancelar_view, name="cancelar"),
]
