from django.urls import path

from . import views

urlpatterns = [
    path("cartera/", views.cartera_centro, name="finanzas_cartera"),
    path("nomina/", views.nomina_lista, name="finanzas_nomina"),
    path("nomina/generar/", views.nomina_generar, name="finanzas_nomina_generar"),
    path("nomina/<int:pk>/", views.nomina_detalle, name="finanzas_nomina_detalle"),
    path("nomina/<int:pk>/pago/", views.nomina_pago_nuevo, name="finanzas_nomina_pago_nuevo"),
    path("nomina/<int:pk>/pagos/<int:pago_pk>/anular/", views.nomina_pago_anular, name="finanzas_nomina_pago_anular"),
    path("facturas/", views.facturas_lista, name="finanzas_facturas"),
    path("facturas/generar/", views.generar_facturas_desde_contratos, name="finanzas_facturas_generar"),
    path("facturas/<int:pk>/", views.factura_detalle, name="finanzas_factura_detalle"),
    path("facturas/<int:pk>/pago/", views.factura_pago_nuevo, name="finanzas_factura_pago_nuevo"),
    path("facturas/<int:pk>/pagos/<int:pago_pk>/anular/", views.factura_pago_anular, name="finanzas_factura_pago_anular"),
    path("flujo/", views.panel_financiero, name="flujo_mensual"),
    path("movimientos/", views.movimientos, name="finanzas_movimientos"),
    path("ingresos/nuevo/", views.ingreso_form, name="finanzas_ingreso_nuevo"),
    path("ingresos/<int:pk>/editar/", views.ingreso_form, name="finanzas_ingreso_editar"),
    path("egresos/nuevo/", views.egreso_form, name="finanzas_egreso_nuevo"),
    path("egresos/<int:pk>/editar/", views.egreso_form, name="finanzas_egreso_editar"),
    path("<str:tipo>/<int:pk>/eliminar/", views.movimiento_eliminar, name="finanzas_movimiento_eliminar"),
]
