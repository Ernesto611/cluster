from django.urls import path
from . import views

urlpatterns = [
    path('listado/', views.listado, name='listado_eventos'),
    path('agregar/', views.agregar, name='agregar_evento'),
    path('<int:idEvento>/detalles/', views.detalles, name='detalles_evento'),
    path('<int:idEvento>/editar/', views.editar, name='editar_evento'),
    path('<int:idEvento>/eliminar/', views.eliminar, name='eliminar_evento'),
    path('<int:idEvento>/alternar_estado/', views.alternar_estado, name='alternar_estado_evento'),
    path('registros/', views.listar_registros_eventos, name='listar_registros_eventos'),
    path('archivos/<int:idEvento>/', views.gestionar_archivos_evento, name='gestionar_archivos_evento'),
    path('archivos/<int:id_archivo>/editar/', views.editar_archivo_evento, name='editar_archivo_evento'),
    path('archivos/<int:id_archivo>/eliminar/', views.eliminar_archivo_evento, name='eliminar_archivo_evento'),
    path('archivos/<int:idArchivo>/alternar_estado/', views.alternar_estado_archivo, name='alternar_estado_archivo'),
    path('categorias/', views.listado_categorias, name='listado_categorias_eventos'),
    path('categorias/agregar/', views.agregar_categoria_evento, name='agregar_categoria_evento'),
    path('categorias/<int:idCategoria>/alternar-estado/', views.alternar_estado_categoria_evento, name='alternar_estado_categoria_evento'),
    path('categorias/<int:idCategoria>/editar/', views.editar_categoria_evento, name='editar_categoria_evento'),
    path('categorias/<int:categoria_id>/estilos/', views.configurar_estilos_categoria, name='configurar_estilos_categoria'),
    path('subcategorias/', views.listado_subcategorias, name='listado_subcategorias_eventos'),
    path('subcategorias/agregar/', views.agregar_subcategoria_evento, name='agregar_subcategoria_evento'),
    path('subcategorias/<int:id>/alternar-estado/', views.alternar_estado_subcategoria_evento, name='alternar_estado_subcategoria_evento'),
    path('subcategorias/<int:id>/editar/', views.editar_subcategoria_evento, name='editar_subcategoria_evento'),
    path('ajax/subcategorias/', views.obtener_subcategorias_por_categoria, name='ajax_obtener_subcategorias'),
]
