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

    # Mantenimientos
    mantenimiento_detalle_view,
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
    inventario_historial_view,
    inventario_ganancias_view,

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
    path("sw.js", sw_js_view, name="sw_js"),
    path("manifest.json", manifest_json_view, name="manifest_json"),
    path("offline/", offline_view, name="offline"),

    # ======================
    # Push
    # ======================
    path("push/vapid_public_key/", vapid_public_key_view, name="vapid_public_key"),
    path("push/save_subscription/", save_subscription_view, name="save_subscription"),
    path("push/delete_subscription/", delete_subscription_view, name="delete_subscription"),
    path("push/status/", push_status_view, name="push_status"),
    path("push/test/", push_test_view, name="push_test"),

    # ======================
    # Notificaciones
    # ======================
    path("notificaciones/", notificaciones_view, name="notificaciones"),
    path("notificaciones/json/", notificaciones_json_view, name="notificaciones_json"),
    path("notificaciones/historial/", notificaciones_historial_view, name="notificaciones_historial"),
    path("notificaciones/<int:pk>/leer/", marcar_notificacion_leida_view, name="marcar_notificacion_leida"),
    path("notificaciones/eliminar/<int:pk>/", notificacion_eliminar_view, name="notificacion_eliminar"),
    path("notificaciones/eliminar-todas/", notificaciones_eliminar_todas_view, name="notificaciones_eliminar_todas"),
    path("notificaciones/marcar-todas-leidas/", marcar_todas_leidas_view, name="marcar_todas_leidas"),
    path("notificaciones/unread-count/", unread_count_view, name="unread_count"),

    # ======================
    # Actividad
    # ======================
    path("actividad/", actividad_historial_view, name="actividad_historial"),

    # ======================
    # Home / Dashboard
    # ======================
    path("", dashboard_view, name="dashboard"),
    path("home/", home_view, name="home"),
    path("inicio/", inicio_view, name="inicio"),

    # ======================
    # Mantenimientos
    # ======================
    path("mantenimientos/historial/", mantenimiento_historial_view, name="mantenimiento_historial"),
    path("mantenimientos/<int:pk>/", mantenimiento_detalle_view, name="mantenimiento_detalle"),
    path("fotos/<int:pk>/eliminar/", foto_mantenimiento_eliminar_view, name="foto_mantenimiento_eliminar"),
    path("usos/<int:pk>/editar/", usoinsumo_editar_view, name="usoinsumo_editar"),
    path("usos/<int:pk>/eliminar/", usoinsumo_eliminar_view, name="usoinsumo_eliminar"),

    # ======================
    # Operativo admin
    # ======================
    path("operativo/", admin_operativo_view, name="admin_operativo"),
    path("operativo/asignar/<int:pk>/", asignar_trabajadores_view, name="asignar_trabajadores"),

    # ====================== 
    # Inventario 
    # ====================== 
    path("inventario/", inventario_view, name="inventario"),
    path("inventario/vender/", vender_insumo_view, name="vender_insumo"),
    path("inventario/agregar/", agregar_stock_view, name="agregar_stock"),
    path("inventario/historial/", inventario_historial_view, name="inventario_historial"),
    path("inventario/ganancias/", inventario_ganancias_view, name="inventario_ganancias"),

    # ======================
    # Finanzas
    # ======================
    path("finanzas/flujo/", flujo_mensual_view, name="flujo_mensual"),
    path("finanzas/ingresos/", ingreso_list_view, name="ingreso_list"),
    path("finanzas/ingresos/nuevo/", ingreso_crear_view, name="ingreso_crear"),
    path("finanzas/ingresos/<int:pk>/editar/", ingreso_editar_view, name="ingreso_editar"),
    path("finanzas/ingresos/<int:pk>/eliminar/", ingreso_eliminar_view, name="ingreso_eliminar"),

    # ======================
    # Reporte de ganancias
    # ======================
    path("finanzas/reporte-ganancias/", reporte_ganancias_view, name="reporte_ganancias"),
    path("finanzas/reporte-ganancias/excel/", exportar_ganancias_excel, name="exportar_ganancias_excel"),
    path("finanzas/reporte-ganancias/pdf/", exportar_ganancias_pdf, name="exportar_ganancias_pdf"),

    # ✅ INGRESOS MANUALES
    path("finanzas/ingresos/manual/nuevo/", ingreso_manual_crear_view, name="ingreso_manual_crear"),
    path("finanzas/ingresos/manual/<int:pk>/eliminar/", ingreso_manual_eliminar_view, name="ingreso_manual_eliminar"),

    # EGRESOS MANUALES
    path("finanzas/egresos/manual/nuevo/", egreso_manual_crear_view, name="egreso_manual_crear"),
    path("finanzas/egresos/manual/<int:pk>/eliminar/", egreso_manual_eliminar_view, name="egreso_manual_eliminar"),

    # ======================
    # Movimientos recurrentes
    # ======================
    path("finanzas/recurrentes/", movimientos_recurrentes_view, name="movimientos_recurrentes"),
    path("finanzas/recurrentes/procesar/", movimientos_recurrentes_procesar_view, name="movimientos_recurrentes_procesar"),
    path("finanzas/recurrentes/<int:pk>/editar/", movimiento_recurrente_editar_view, name="movimiento_recurrente_editar"),
    path("finanzas/recurrentes/<int:pk>/toggle/", movimiento_recurrente_toggle_view, name="movimiento_recurrente_toggle"),
    path("finanzas/recurrentes/<int:pk>/eliminar/", movimiento_recurrente_eliminar_view, name="movimiento_recurrente_eliminar"),
]