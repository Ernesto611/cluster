from django.urls import path
from . import views

urlpatterns = [
    path('listado/', views.listado, name='listado_actividades'),
    path('agregar/', views.agregar_actividad, name='agregar_actividad'),
    path('<int:idActividad>/editar/', views.editar_actividad, name='editar_actividad'),
    path('<int:idActividad>/detalles/', views.detalles_actividad, name='detalles_actividad'),
    path('<int:idActividad>/alternar-estado/', views.alternar_estado_actividad, name='alternar_estado_actividad'),
    path('<int:idActividad>/eliminar/', views.eliminar_actividad, name='eliminar_actividad'),
    path('registros/actividades/', views.listar_registros_actividades, name='listar_registros_actividades'),
    path('ajax/actividades-por-evento/', views.obtener_actividades_por_evento, name='ajax_actividades_por_evento'),
    path('tipos/', views.listado_tipos, name='listado_tipos_actividades'),
    path('tipos/agregar/', views.agregar_tipo_actividad, name='agregar_tipo_actividad'),
    path('tipos/<int:idTipo>/alternar-estado/', views.alternar_estado_tipo_actividad, name='alternar_estado_tipo_actividad'),
    path('tipos/<int:idTipo>/editar/', views.editar_tipo_actividad, name='editar_tipo_actividad'),
    path('tipos/<int:idTipo>/eliminar/', views.eliminar_tipo_actividad, name='eliminar_tipo_actividad'),
]
