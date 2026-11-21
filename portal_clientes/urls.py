from . import soporte
from django.urls import path
from . import views
app_name = 'portal_clientes'
urlpatterns = [path('activar/', views.activar, name='activar'), path('ingresar/', views.ingresar, name='ingresar'), path('inicio/', views.inicio, name='inicio'), path('mantenimientos/', views.mantenimientos, name='mantenimientos'), path('mantenimientos/<int:pk>/', views.mantenimiento_detalle, name='mantenimiento_detalle'), path('proximas-visitas/', views.proximas_visitas, name='proximas_visitas'), path('mantenimientos/<int:pk>/fotos/<int:foto_id>/', views.foto_mantenimiento, name='foto_mantenimiento'), path('mis-pagos/', views.mis_pagos, name='mis_pagos'), path('contratos/<int:pk>/', views.mi_contrato, name='mi_contrato'), path('salir/', views.salir, name='salir')]

urlpatterns += [path('soporte/', soporte.soporte_cliente, name='soporte'), path('soporte/<int:pk>/', soporte.soporte_conversacion, name='soporte_conversacion')]

urlpatterns += [path('soporte/<int:pk>/actualizaciones/', soporte.soporte_actualizaciones, name='soporte_actualizaciones'), path('soporte/contadores/', soporte.soporte_contadores, name='soporte_contadores')]

urlpatterns += [path('soporte/archivos/<int:pk>/', soporte.soporte_archivo_cliente, name='soporte_archivo')]

from . import notificaciones
urlpatterns += [
    path('notificaciones/', notificaciones.lista, name='notificaciones'),
    path('notificaciones/contador/', notificaciones.contador, name='notificaciones_contador'),
    path('notificaciones/<int:pk>/abrir/', notificaciones.abrir, name='notificacion_abrir'),
    path('notificaciones/marcar-todas/', notificaciones.marcar_todas, name='notificaciones_marcar_todas'),
]
