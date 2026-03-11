from django.urls import path
from .views import (
    sw_js_view,
    manifest_json_view,
    offline_view,
    vapid_public_key_view,
    save_subscription_view,
    push_test_view,
    unread_count_view,
    inicio_view,
    home_view,
    dashboard_view,
    mantenimiento_detalle_view,
    usoinsumo_eliminar_view,
    usoinsumo_editar_view,
    admin_operativo_view,
    asignar_trabajadores_view,
    flujo_mensual_view,
    ingreso_list_view,
    ingreso_crear_view,
    ingreso_editar_view,
    ingreso_eliminar_view,
)

urlpatterns = [
    path("sw.js", sw_js_view, name="sw_js"),
    path("manifest.json", manifest_json_view, name="manifest_json"),
    path("offline/", offline_view, name="offline"),

    path("push/vapid_public_key/", vapid_public_key_view, name="vapid_public_key"),
    path("push/save_subscription/", save_subscription_view, name="save_subscription"),
    path("push/test/", push_test_view, name="push_test"),

    path("notificaciones/unread-count/", unread_count_view, name="unread_count"),

    path("", dashboard_view, name="dashboard"),
    path("home/", home_view, name="home"),
    path("inicio/", inicio_view, name="inicio"),
    path("mis/", dashboard_view, name="mis_mantenimientos"),

    path("mantenimientos/<int:pk>/", mantenimiento_detalle_view, name="mantenimiento_detalle"),
    path("usos/<int:pk>/editar/", usoinsumo_editar_view, name="usoinsumo_editar"),
    path("usos/<int:pk>/eliminar/", usoinsumo_eliminar_view, name="usoinsumo_eliminar"),

    path("operativo/", admin_operativo_view, name="admin_operativo"),
    path("operativo/asignar/<int:pk>/", asignar_trabajadores_view, name="asignar_trabajadores"),

    path("finanzas/flujo/", flujo_mensual_view, name="flujo_mensual"),
    path("finanzas/ingresos/", ingreso_list_view, name="ingreso_list"),
    path("finanzas/ingresos/nuevo/", ingreso_crear_view, name="ingreso_crear"),
    path("finanzas/ingresos/<int:pk>/editar/", ingreso_editar_view, name="ingreso_editar"),
    path("finanzas/ingresos/<int:pk>/eliminar/", ingreso_eliminar_view, name="ingreso_eliminar"),
]