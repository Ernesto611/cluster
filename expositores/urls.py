from django.urls import path
from . import views

urlpatterns = [
    path('listado/', views.listado, name='listado_expositores'),
    path('agregar/', views.agregar, name='agregar_expositor'),
    path('<int:idExpositor>/detalles/', views.detalles, name='detalles_expositor'),
    path('<int:idExpositor>/editar/', views.editar, name='editar_expositor'),
    path('<int:idExpositor>/eliminar/', views.eliminar, name='eliminar_expositor'),
    path('asignar_actividades/<int:id_expositor>/', views.asignar_actividades_expositor, name='asignar_actividades_expositor'),
    path('archivos/<int:idExpositor>/', views.gestionar_archivos_expositor, name='gestionar_archivos_expositor'),
    path('archivos/<int:id_archivo>/editar/', views.editar_archivo_expositor, name='editar_archivo_expositor'),
    path('archivos/<int:id_archivo>/eliminar/', views.eliminar_archivo_expositor, name='eliminar_archivo_expositor'),
]
