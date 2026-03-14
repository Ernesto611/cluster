from django.urls import path
from . import views

urlpatterns = [
    path('agregar/', views.agregar, name='agregar_agenda'),
    path('obtener_actividades_json/', views.obtener_actividades_json, name='obtener_actividades_json'),
    path('listado/', views.listado, name='listado_agendas'),
    path('eliminar/<int:idAgenda>/', views.eliminar, name='eliminar_agenda'),
    path('<int:idAgenda>/alternar-estado/', views.alternar_estado_agenda, name='alternar_estado_agenda'),
    path('editar/<int:idAgenda>/', views.editar, name='editar_agenda'),
    path('detalles/<int:idAgenda>/', views.detalles, name='detalles_agenda'),
    path('obtener-actividades/', views.obtener_actividades_por_evento, name='obtener_actividades_por_evento'),
]
