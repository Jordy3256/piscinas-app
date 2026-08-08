from django.urls import path

from .views import (
    # PWA
    sw_js_view,
    manifest_json_view,
    offline_view,

    # Push
    vapid_public_key_view,
    save_subscription_view,
    delete_subscription_view,
    push_status_view,
    push_test_view,

    # Notificaciones
    unread_count_view,
    notificaciones_view,
    notificaciones_json_view,
    notificaciones_historial_view,
    marcar_notificacion_leida_view,
    notificacion_eliminar_view,
    notificaciones_eliminar_todas_view,
    marcar_todas_leidas_view,

    # Actividad
    actividad_historial_view,

    # Core
    inicio_view,
    home_view,
    dashboard_view,
    calculadora_quimicos_view,
    mi_cuenta_trabajador_view,

    # Clientes y contratos
    cliente_list_view,
    cliente_crear_view,
    cliente_editar_view,
    cliente_detalle_view,
    cliente_crear_rapido_view,
    contrato_list_view,
    contrato_crear_view,
    contrato_editar_view,
    contrato_detalle_view,
    contrato_regenerar_programacion_view,
    contrato_toggle_view,

    # Mantenimientos
    mantenimiento_detalle_view,
    mantenimiento_whatsapp_cliente_view,
    mantenimiento_historial_view,
    foto_mantenimiento_eliminar_view,
    usoinsumo_eliminar_view,
    usoinsumo_editar_view,

    # Operativo admin
    admin_operativo_view,
    asignar_trabajadores_view,

    # Inventario
    inventario_view,
    vender_insumo_view,
    agregar_stock_view,
    compra_inventario_view,
    inventario_entrega_trabajador_view,
    inventario_devolucion_trabajador_view,
    inventario_historial_view,
    inventario_trabajador_detalle_view,
    inventario_general_pdf_view,
    inventario_trabajador_pdf_view,
    inventario_kardex_pdf_view,
    inventario_movimientos_pdf_view,
    inventario_ventas_pdf_view,
    inventario_compras_pdf_view,
    inventario_productos_view,
    inventario_producto_crear_view,
    inventario_producto_editar_view,
    inventario_producto_detalle_view,
    inventario_producto_ajustar_stock_view,
    inventario_producto_toggle_view,
    inventario_producto_eliminar_view,
    inventario_presentacion_agregar_view,
    inventario_presentacion_eliminar_view,
    mi_inventario_trabajador_view,
    solicitud_reposicion_crear_view,
    solicitud_reposicion_atender_view,
    inventario_productos_criticos_pdf_view,
    inventario_consumo_trabajadores_pdf_view,
    inventario_consumo_contratos_pdf_view,

    # Finanzas
    flujo_mensual_view,
    ingreso_list_view,
    ingreso_crear_view,
    ingreso_editar_view,
    ingreso_eliminar_view,
    ingreso_manual_crear_view,
    ingreso_manual_eliminar_view,
    egreso_manual_crear_view,
    egreso_manual_eliminar_view,

    # Facturación
    factura_list_view,
    factura_detalle_view,
    factura_generar_mes_view,
    factura_marcar_pagada_view,
    factura_anular_view,

    # Reporte de ganancias
    reporte_ganancias_view,
    exportar_ganancias_excel,
    exportar_ganancias_pdf,

    # Recurrentes
    movimientos_recurrentes_view,
    movimientos_recurrentes_procesar_view,
    movimiento_recurrente_editar_view,
    movimiento_recurrente_toggle_view,
    movimiento_recurrente_eliminar_view,
)


urlpatterns = [
    # ======================
    # PWA
    # ======================
    path(
        "sw.js",
        sw_js_view,
        name="sw_js",
    ),
    path(
        "manifest.json",
        manifest_json_view,
        name="manifest_json",
    ),
    path(
        "offline/",
        offline_view,
        name="offline",
    ),

    # ======================
    # Push
    # ======================
    path(
        "push/vapid_public_key/",
        vapid_public_key_view,
        name="vapid_public_key",
    ),
    path(
        "push/save_subscription/",
        save_subscription_view,
        name="save_subscription",
    ),
    path(
        "push/delete_subscription/",
        delete_subscription_view,
        name="delete_subscription",
    ),
    path(
        "push/status/",
        push_status_view,
        name="push_status",
    ),
    path(
        "push/test/",
        push_test_view,
        name="push_test",
    ),

    # ======================
    # Notificaciones
    # ======================
    path(
        "notificaciones/",
        notificaciones_view,
        name="notificaciones",
    ),
    path(
        "notificaciones/json/",
        notificaciones_json_view,
        name="notificaciones_json",
    ),
    path(
        "notificaciones/historial/",
        notificaciones_historial_view,
        name="notificaciones_historial",
    ),
    path(
        "notificaciones/<int:pk>/leer/",
        marcar_notificacion_leida_view,
        name="marcar_notificacion_leida",
    ),
    path(
        "notificaciones/eliminar/<int:pk>/",
        notificacion_eliminar_view,
        name="notificacion_eliminar",
    ),
    path(
        "notificaciones/eliminar-todas/",
        notificaciones_eliminar_todas_view,
        name="notificaciones_eliminar_todas",
    ),
    path(
        "notificaciones/marcar-todas-leidas/",
        marcar_todas_leidas_view,
        name="marcar_todas_leidas",
    ),
    path(
        "notificaciones/unread-count/",
        unread_count_view,
        name="unread_count",
    ),

    # ======================
    # Actividad
    # ======================
    path(
        "actividad/",
        actividad_historial_view,
        name="actividad_historial",
    ),

    # ======================
    # Home / Dashboard
    # ======================
    path(
        "",
        dashboard_view,
        name="dashboard",
    ),
    path(
        "home/",
        home_view,
        name="home",
    ),
    path(
        "inicio/",
        inicio_view,
        name="inicio",
    ),
    path(
        "herramientas/calculadora-quimicos/",
        calculadora_quimicos_view,
        name="calculadora_quimicos",
    ),
    path("mi-cuenta/", mi_cuenta_trabajador_view, name="mi_cuenta_trabajador"),

    # ======================
    # Clientes y contratos
    # ======================
    path("clientes/", cliente_list_view, name="cliente_list"),
    path("clientes/nuevo/", cliente_crear_view, name="cliente_crear"),
    path("clientes/crear-rapido/", cliente_crear_rapido_view, name="cliente_crear_rapido"),
    path("clientes/<int:pk>/", cliente_detalle_view, name="cliente_detalle"),
    path("clientes/<int:pk>/editar/", cliente_editar_view, name="cliente_editar"),

    # ======================
    # Contratos
    # ======================
    path(
        "contratos/",
        contrato_list_view,
        name="contrato_list",
    ),
    path(
        "contratos/nuevo/",
        contrato_crear_view,
        name="contrato_crear",
    ),
    path(
        "contratos/<int:pk>/",
        contrato_detalle_view,
        name="contrato_detalle",
    ),
    path(
        "contratos/<int:pk>/editar/",
        contrato_editar_view,
        name="contrato_editar",
    ),
    path(
        "contratos/<int:pk>/regenerar-programacion/",
        contrato_regenerar_programacion_view,
        name="contrato_regenerar_programacion",
    ),
    path(
        "contratos/<int:pk>/toggle/",
        contrato_toggle_view,
        name="contrato_toggle",
    ),

    # ======================
    # Mantenimientos
    # ======================
    path(
        "mantenimientos/historial/",
        mantenimiento_historial_view,
        name="mantenimiento_historial",
    ),
    path(
        "mantenimientos/<int:pk>/",
        mantenimiento_detalle_view,
        name="mantenimiento_detalle",
    ),
    path(
        "mantenimientos/<int:pk>/whatsapp/",
        mantenimiento_whatsapp_cliente_view,
        name="mantenimiento_whatsapp_cliente",
    ),
    path(
        "fotos/<int:pk>/eliminar/",
        foto_mantenimiento_eliminar_view,
        name="foto_mantenimiento_eliminar",
    ),
    path(
        "usos/<int:pk>/editar/",
        usoinsumo_editar_view,
        name="usoinsumo_editar",
    ),
    path(
        "usos/<int:pk>/eliminar/",
        usoinsumo_eliminar_view,
        name="usoinsumo_eliminar",
    ),

    # ======================
    # Operativo admin
    # ======================
    path(
        "operativo/",
        admin_operativo_view,
        name="admin_operativo",
    ),
    path(
        "operativo/asignar/<int:pk>/",
        asignar_trabajadores_view,
        name="asignar_trabajadores",
    ),

    # ======================
    # Inventario
    # ======================
    path(
        "inventario/",
        inventario_view,
        name="inventario",
    ),
    path(
        "inventario/vender/",
        vender_insumo_view,
        name="vender_insumo",
    ),
    path(
        "inventario/agregar/",
        agregar_stock_view,
        name="agregar_stock",
    ),
    path(
        "inventario/historial/",
        inventario_historial_view,
        name="inventario_historial",
    ),
    path("inventario/comprar/", compra_inventario_view, name="compra_inventario"),
    path("inventario/entregar/", inventario_entrega_trabajador_view, name="inventario_entrega_trabajador"),
    path("inventario/devolver/", inventario_devolucion_trabajador_view, name="inventario_devolucion_trabajador"),
    path("inventario/trabajador/<int:trabajador_id>/", inventario_trabajador_detalle_view, name="inventario_trabajador_detalle"),
    path("inventario/pdf/general/", inventario_general_pdf_view, name="inventario_general_pdf"),
    path("inventario/pdf/trabajador/<int:trabajador_id>/", inventario_trabajador_pdf_view, name="inventario_trabajador_pdf"),
    path("inventario/pdf/kardex/<int:insumo_id>/", inventario_kardex_pdf_view, name="inventario_kardex_pdf"),
    path("inventario/pdf/movimientos/", inventario_movimientos_pdf_view, name="inventario_movimientos_pdf"),
    path("inventario/pdf/ventas/", inventario_ventas_pdf_view, name="inventario_ventas_pdf"),
    path("inventario/pdf/compras/", inventario_compras_pdf_view, name="inventario_compras_pdf"),
    path("inventario/productos/", inventario_productos_view, name="inventario_productos"),
    path("inventario/productos/nuevo/", inventario_producto_crear_view, name="inventario_producto_crear"),
    path("inventario/productos/<int:pk>/", inventario_producto_detalle_view, name="inventario_producto_detalle"),
    path("inventario/productos/<int:pk>/editar/", inventario_producto_editar_view, name="inventario_producto_editar"),
    path("inventario/productos/<int:pk>/ajustar-stock/", inventario_producto_ajustar_stock_view, name="inventario_producto_ajustar_stock"),
    path("inventario/productos/<int:pk>/toggle/", inventario_producto_toggle_view, name="inventario_producto_toggle"),
    path("inventario/productos/<int:pk>/eliminar/", inventario_producto_eliminar_view, name="inventario_producto_eliminar"),
    path("inventario/productos/<int:pk>/presentaciones/agregar/", inventario_presentacion_agregar_view, name="inventario_presentacion_agregar"),
    path("inventario/presentaciones/<int:pk>/eliminar/", inventario_presentacion_eliminar_view, name="inventario_presentacion_eliminar"),
    path("mi-inventario/", mi_inventario_trabajador_view, name="mi_inventario_trabajador"),
    path("mi-inventario/reposicion/<int:insumo_id>/", solicitud_reposicion_crear_view, name="solicitud_reposicion_crear"),
    path("inventario/reposicion/<int:pk>/atender/", solicitud_reposicion_atender_view, name="solicitud_reposicion_atender"),
    path("inventario/pdf/productos-criticos/", inventario_productos_criticos_pdf_view, name="inventario_productos_criticos_pdf"),
    path("inventario/pdf/consumo-trabajadores/", inventario_consumo_trabajadores_pdf_view, name="inventario_consumo_trabajadores_pdf"),
    path("inventario/pdf/consumo-contratos/", inventario_consumo_contratos_pdf_view, name="inventario_consumo_contratos_pdf"),

    # ======================
    # Finanzas
    # ======================
    path(
        "finanzas/flujo/",
        flujo_mensual_view,
        name="flujo_mensual",
    ),
    path(
        "finanzas/ingresos/",
        ingreso_list_view,
        name="ingreso_list",
    ),
    path(
        "finanzas/ingresos/nuevo/",
        ingreso_crear_view,
        name="ingreso_crear",
    ),
    path(
        "finanzas/ingresos/<int:pk>/editar/",
        ingreso_editar_view,
        name="ingreso_editar",
    ),
    path(
        "finanzas/ingresos/<int:pk>/eliminar/",
        ingreso_eliminar_view,
        name="ingreso_eliminar",
    ),

    # ======================
    # Facturación
    # ======================
    path(
        "finanzas/facturas/",
        factura_list_view,
        name="factura_list",
    ),
    path(
        "finanzas/facturas/generar/",
        factura_generar_mes_view,
        name="factura_generar_mes",
    ),
    path(
        "finanzas/facturas/<int:pk>/",
        factura_detalle_view,
        name="factura_detalle",
    ),
    path(
        "finanzas/facturas/<int:pk>/pagar/",
        factura_marcar_pagada_view,
        name="factura_marcar_pagada",
    ),
    path(
        "finanzas/facturas/<int:pk>/anular/",
        factura_anular_view,
        name="factura_anular",
    ),

    # ======================
    # Reporte de ganancias
    # ======================
    path(
        "finanzas/reporte-ganancias/",
        reporte_ganancias_view,
        name="reporte_ganancias",
    ),
    path(
        "finanzas/reporte-ganancias/excel/",
        exportar_ganancias_excel,
        name="exportar_ganancias_excel",
    ),
    path(
        "finanzas/reporte-ganancias/pdf/",
        exportar_ganancias_pdf,
        name="exportar_ganancias_pdf",
    ),

    # ======================
    # Ingresos manuales
    # ======================
    path(
        "finanzas/ingresos/manual/nuevo/",
        ingreso_manual_crear_view,
        name="ingreso_manual_crear",
    ),
    path(
        "finanzas/ingresos/manual/<int:pk>/eliminar/",
        ingreso_manual_eliminar_view,
        name="ingreso_manual_eliminar",
    ),

    # ======================
    # Egresos manuales
    # ======================
    path(
        "finanzas/egresos/manual/nuevo/",
        egreso_manual_crear_view,
        name="egreso_manual_crear",
    ),
    path(
        "finanzas/egresos/manual/<int:pk>/eliminar/",
        egreso_manual_eliminar_view,
        name="egreso_manual_eliminar",
    ),

    # ======================
    # Movimientos recurrentes
    # ======================
    path(
        "finanzas/recurrentes/",
        movimientos_recurrentes_view,
        name="movimientos_recurrentes",
    ),
    path(
        "finanzas/recurrentes/procesar/",
        movimientos_recurrentes_procesar_view,
        name="movimientos_recurrentes_procesar",
    ),
    path(
        "finanzas/recurrentes/<int:pk>/editar/",
        movimiento_recurrente_editar_view,
        name="movimiento_recurrente_editar",
    ),
    path(
        "finanzas/recurrentes/<int:pk>/toggle/",
        movimiento_recurrente_toggle_view,
        name="movimiento_recurrente_toggle",
    ),
    path(
        "finanzas/recurrentes/<int:pk>/eliminar/",
        movimiento_recurrente_eliminar_view,
        name="movimiento_recurrente_eliminar",
    ),
]