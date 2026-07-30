from django.urls import path

from . import views

urlpatterns = [
    path("flujo/", views.panel_financiero, name="flujo_mensual"),
    path("movimientos/", views.movimientos, name="finanzas_movimientos"),
    path("ingresos/nuevo/", views.ingreso_form, name="finanzas_ingreso_nuevo"),
    path("ingresos/<int:pk>/editar/", views.ingreso_form, name="finanzas_ingreso_editar"),
    path("egresos/nuevo/", views.egreso_form, name="finanzas_egreso_nuevo"),
    path("egresos/<int:pk>/editar/", views.egreso_form, name="finanzas_egreso_editar"),
    path("<str:tipo>/<int:pk>/eliminar/", views.movimiento_eliminar, name="finanzas_movimiento_eliminar"),
]
