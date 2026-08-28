from django.urls import path

from . import views

urlpatterns = [
    path("resumen-mensual.pdf", views.resumen_mensual_cobros_pagos_pdf, name="finanzas_resumen_mensual_pdf"),
    path("cartera/", views.cartera_centro, name="finanzas_cartera"),
    path("calendario/", views.calendario_financiero, name="finanzas_calendario"),
    path("clientes/<int:cliente_pk>/estado-cuenta.pdf", views.cliente_estado_cuenta_pdf, name="finanzas_cliente_estado_cuenta_pdf"),
    path("nomina/", views.nomina_lista, name="finanzas_nomina"),
    path("nomina/generar/", views.nomina_generar, name="finanzas_nomina_generar"),
    path("nomina/trabajador/<int:trabajador_pk>/configuracion/", views.trabajador_configuracion_pago, name="finanzas_trabajador_configuracion_pago"),
    path("nomina/trabajador/<int:trabajador_pk>/pagar/", views.nomina_pago_consolidado, name="finanzas_nomina_pago_consolidado"),
    path("nomina/pagos-consolidados/<int:lote_pk>/comprobante.pdf", views.nomina_pago_consolidado_pdf, name="finanzas_nomina_pago_consolidado_pdf"),
    path("nomina/trabajador/<int:trabajador_pk>/pdf/", views.nomina_trabajador_pdf, name="finanzas_nomina_trabajador_pdf"),
    path("nomina/<int:pk>/", views.nomina_detalle, name="finanzas_nomina_detalle"),
    path("nomina/<int:pk>/pago/", views.nomina_pago_nuevo, name="finanzas_nomina_pago_nuevo"),
    path("nomina/<int:pk>/pagos/<int:pago_pk>/anular/", views.nomina_pago_anular, name="finanzas_nomina_pago_anular"),
    path("facturas/", views.facturas_lista, name="finanzas_facturas"),
    path("facturas/generar/", views.generar_facturas_desde_contratos, name="finanzas_facturas_generar"),
    path("facturas/<int:pk>/", views.factura_detalle, name="finanzas_factura_detalle"),
    path("facturas/<int:pk>/pago/", views.factura_pago_nuevo, name="finanzas_factura_pago_nuevo"),
    path("facturas/<int:pk>/pagos/<int:pago_pk>/anular/", views.factura_pago_anular, name="finanzas_factura_pago_anular"),
    path("pagos/factura/<int:pago_pk>/comprobante.pdf", views.pago_factura_comprobante_pdf, name="finanzas_pago_factura_comprobante_pdf"),
    path("pagos/trabajador/<int:pago_pk>/comprobante.pdf", views.pago_trabajador_comprobante_pdf, name="finanzas_pago_trabajador_comprobante_pdf"),
    path("flujo/", views.panel_financiero, name="flujo_mensual"),
    path("movimientos/", views.movimientos, name="finanzas_movimientos"),
    path("ingresos/nuevo/", views.ingreso_form, name="finanzas_ingreso_nuevo"),
    path("ingresos/<int:pk>/editar/", views.ingreso_form, name="finanzas_ingreso_editar"),
    path("egresos/nuevo/", views.egreso_form, name="finanzas_egreso_nuevo"),
    path("egresos/<int:pk>/editar/", views.egreso_form, name="finanzas_egreso_editar"),
    path("<str:tipo>/<int:pk>/eliminar/", views.movimiento_eliminar, name="finanzas_movimiento_eliminar"),
]
