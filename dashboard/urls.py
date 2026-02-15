from django.urls import path
from .views import offline_view
from .views import home_view
from .views import (
    dashboard_view,
    mantenimiento_detalle_view,
    usoinsumo_eliminar_view,
    usoinsumo_editar_view,
    admin_operativo_view,
    asignar_trabajadores_view,
    flujo_mensual_view,

    # ✅ NUEVO: Ingresos manuales
    ingreso_list_view,
    ingreso_crear_view,
    ingreso_editar_view,
    ingreso_eliminar_view,
)

urlpatterns = [
    path('home/', home_view, name='home'),
    path('', dashboard_view, name='dashboard'),
    path("offline/", offline_view, name="offline"),

    # -----------------------------
    # Mantenimientos
    # -----------------------------
    path('mantenimientos/<int:pk>/', mantenimiento_detalle_view, name='mantenimiento_detalle'),

    # -----------------------------
    # Uso de insumos
    # -----------------------------
    path('usos/<int:pk>/editar/', usoinsumo_editar_view, name='usoinsumo_editar'),
    path('usos/<int:pk>/eliminar/', usoinsumo_eliminar_view, name='usoinsumo_eliminar'),

    # -----------------------------
    # Operativo admin
    # -----------------------------
    path('operativo/', admin_operativo_view, name='admin_operativo'),
    path('operativo/asignar/<int:pk>/', asignar_trabajadores_view, name='asignar_trabajadores'),

    # -----------------------------
    # Finanzas
    # -----------------------------
    path('finanzas/flujo/', flujo_mensual_view, name='flujo_mensual'),

    # ✅ NUEVO: Gestión manual de ingresos
    path('finanzas/ingresos/', ingreso_list_view, name='ingresos_list'),
    path('finanzas/ingresos/nuevo/', ingreso_crear_view, name='ingreso_crear'),
    path('finanzas/ingresos/<int:pk>/editar/', ingreso_editar_view, name='ingreso_editar'),
    path('finanzas/ingresos/<int:pk>/eliminar/', ingreso_eliminar_view, name='ingreso_eliminar'),
]
