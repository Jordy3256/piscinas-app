from django.urls import path
from . import views

app_name = "asistente_tecnico"

urlpatterns = [
    path("", views.asistente_inicio_view, name="inicio"),
    path("historial/", views.asistente_historial_view, name="historial"),
    # Compatibilidad: la biblioteca antigua redirige conceptualmente a la biblioteca técnica nueva.
    path("biblioteca/", views.biblioteca_tecnica_view, name="biblioteca"),
    path("centro/", views.centro_conocimiento_view, name="centro_conocimiento"),
    path("academia/", views.academia_view, name="academia"),
    path("academia/leccion/<int:pk>/", views.leccion_detalle_view, name="leccion_detalle"),
    path("academia/leccion/<int:pk>/completar/", views.leccion_completar_view, name="leccion_completar"),
    path("biblioteca/articulo/<int:pk>/", views.articulo_biblioteca_detalle_view, name="biblioteca_detalle"),
    path("casos-reales/", views.casos_reales_view, name="casos_reales"),
    path("certificacion/", views.certificacion_view, name="certificacion"),
    path("casos/<int:pk>/", views.asistente_caso_detalle_view, name="caso_detalle"),
    path("casos/<int:pk>/seguimiento/", views.asistente_seguimiento_view, name="seguimiento"),
    path("administracion/", views.asistente_admin_view, name="admin"),
    path("administracion/conocimiento/", views.conocimiento_admin_view, name="conocimiento_admin"),
    path("administracion/conocimiento/motor/", views.motor_conocimiento_view, name="motor_conocimiento"),
    path("administracion/conocimiento/motor/analizar/", views.motor_conocimiento_analizar_view, name="motor_conocimiento_analizar"),
    path("administracion/conocimiento/propuesta/<int:pk>/estado/", views.propuesta_conocimiento_estado_view, name="propuesta_conocimiento_estado"),
    path("administracion/conocimiento/categoria/nueva/", views.categoria_form_view, name="categoria_nueva"),
    path("administracion/conocimiento/categoria/<int:pk>/editar/", views.categoria_form_view, name="categoria_editar"),
    path("administracion/conocimiento/leccion/nueva/", views.leccion_form_view, name="leccion_nueva"),
    path("administracion/conocimiento/leccion/<int:pk>/editar/", views.leccion_form_view, name="leccion_editar"),
    path("administracion/conocimiento/articulo/nuevo/", views.articulo_form_view, name="articulo_nuevo"),
    path("administracion/conocimiento/articulo/<int:pk>/editar/", views.articulo_form_view, name="articulo_editar"),
    path("administracion/conocimiento/consejo/nuevo/", views.consejo_form_view, name="consejo_nuevo"),
    path("administracion/conocimiento/consejo/<int:pk>/editar/", views.consejo_form_view, name="consejo_editar"),
    path("administracion/version/nueva/", views.asistente_version_nueva_view, name="version_nueva"),
    path("administracion/version/<int:pk>/activar/", views.asistente_version_activar_view, name="version_activar"),
    path("administracion/casos/<int:pk>/destacar/", views.asistente_destacar_view, name="destacar"),

    # Academia JVAQUA CMS 3.1
    path("academia-jvaqua/", views.academia_publica_view, name="academia_cms"),
    path("academia-jvaqua/contenido/<slug:slug>/", views.academia_contenido_detalle_view, name="academia_contenido_detalle"),
    path("academia-jvaqua/contenido/<slug:slug>/completar/", views.academia_contenido_completar_view, name="academia_contenido_completar"),
    path("academia-jvaqua/contenido/<slug:slug>/favorito/", views.academia_contenido_favorito_view, name="academia_contenido_favorito"),
    path("academia-jvaqua/pdf/manual/", views.academia_pdf_manual_view, name="academia_pdf_manual"),
    path("academia-jvaqua/pdf/categoria/<str:tipo>/", views.academia_pdf_categoria_view, name="academia_pdf_categoria"),
    path("academia-jvaqua/pdf/<slug:slug>/", views.academia_pdf_articulo_view, name="academia_pdf_articulo"),
    path("administracion/academia-cms/", views.academia_cms_admin_view, name="cms_admin"),
    path("administracion/academia-cms/contenido/nuevo/", views.academia_cms_contenido_form_view, name="cms_contenido_nuevo"),
    path("administracion/academia-cms/contenido/<int:pk>/editar/", views.academia_cms_contenido_form_view, name="cms_contenido_editar"),
    path("administracion/academia-cms/contenido/<int:contenido_pk>/imagen/", views.academia_cms_imagen_form_view, name="cms_imagen_nueva"),
    path("administracion/academia-cms/imagen/<int:pk>/eliminar/", views.academia_cms_imagen_eliminar_view, name="cms_imagen_eliminar"),
    path("administracion/academia-cms/experiencias/", views.experiencias_conocimiento_view, name="cms_experiencias"),
    path("administracion/academia-cms/experiencia/nueva/", views.experiencia_conocimiento_form_view, name="cms_experiencia_nueva"),
    path("administracion/academia-cms/experiencia/<int:pk>/editar/", views.experiencia_conocimiento_form_view, name="cms_experiencia_editar"),
    path("administracion/academia-cms/experiencia/<int:pk>/convertir/", views.experiencia_convertir_view, name="cms_experiencia_convertir"),
]
