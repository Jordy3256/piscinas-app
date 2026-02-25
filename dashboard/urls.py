from django.urls import path
from .views import (
    # PWA
    sw_js_view,
    manifest_json_view,
    offline_view,

    # ✅ Push
    vapid_public_key_view,
    save_subscription_view,
    push_test_view,

    # Notificaciones (evita 404)
    unread_count_view,

    # Core
    home_view,
    dashboard_view,

    # Mantenimientos
    mantenimiento_detalle_view,
    usoinsumo_eliminar_view,
    usoinsumo_editar_view,

    # Operativo admin
    admin_operativo_view,
    asignar_trabajadores_view,

    # Finanzas
    flujo_mensual_view,
    ingreso_list_view,
    ingreso_crear_view,
    ingreso_editar_view,
    ingreso_eliminar_view,
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
    path("push/test/", push_test_view, name="push_test"),

    # 👇 Esto elimina el 404 del badge
    path("notificaciones/unread-count/", unread_count_view, name="unread_count"),

    # ======================
    # Home / Dashboard
    # ======================
    path("", dashboard_root_view,name="dashboard_root"),
    path("home/", home_view, name="home"),
    path("", dashboard_view, name="dashboard"),

    # ======================
    # Mantenimientos
    # ======================
    path("mantenimientos/<int:pk>/", mantenimiento_detalle_view, name="mantenimiento_detalle"),

    # Uso de insumos
    path("usos/<int:pk>/editar/", usoinsumo_editar_view, name="usoinsumo_editar"),
    path("usos/<int:pk>/eliminar/", usoinsumo_eliminar_view, name="usoinsumo_eliminar"),

    # ======================
    # Operativo admin
    # ======================
    path("operativo/", admin_operativo_view, name="admin_operativo"),
    path("operativo/asignar/<int:pk>/", asignar_trabajadores_view, name="asignar_trabajadores"),

    # ======================
    # Finanzas
    # ======================
    path("finanzas/flujo/", flujo_mensual_view, name="flujo_mensual"),
    path("finanzas/ingresos/", ingreso_list_view, name="ingresos_list"),
    path("finanzas/ingresos/nuevo/", ingreso_crear_view, name="ingreso_crear"),
    path("finanzas/ingresos/<int:pk>/editar/", ingreso_editar_view, name="ingreso_editar"),
    path("finanzas/ingresos/<int:pk>/eliminar/", ingreso_eliminar_view, name="ingreso_eliminar"),
]