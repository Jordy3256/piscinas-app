from django.urls import path
from . import views
app_name = 'portal_clientes'
urlpatterns = [path('activar/', views.activar, name='activar'), path('ingresar/', views.ingresar, name='ingresar'), path('inicio/', views.inicio, name='inicio'), path('mantenimientos/', views.mantenimientos, name='mantenimientos'), path('mantenimientos/<int:pk>/', views.mantenimiento_detalle, name='mantenimiento_detalle'), path('proximas-visitas/', views.proximas_visitas, name='proximas_visitas'), path('mantenimientos/<int:pk>/fotos/<int:foto_id>/', views.foto_mantenimiento, name='foto_mantenimiento'), path('mis-pagos/', views.mis_pagos, name='mis_pagos'), path('salir/', views.salir, name='salir')]
