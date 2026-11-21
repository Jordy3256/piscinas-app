from django.urls import path
from . import views
app_name = 'portal_clientes'
urlpatterns = [path('activar/', views.activar, name='activar'), path('ingresar/', views.ingresar, name='ingresar'), path('inicio/', views.inicio, name='inicio'), path('salir/', views.salir, name='salir')]
