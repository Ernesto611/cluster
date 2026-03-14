from django.urls import path
from . import views

urlpatterns = [
    path('listado/', views.listado_notificaciones, name='listado_notificaciones'),
    path('agregar/', views.agregar_notificacion, name='agregar_notificacion'),
    path('editar/<int:pk>/', views.editar_notificacion, name='editar_notificacion'),
    path('enviar/<int:pk>/', views.enviar_notificacion, name='enviar_notificacion'),
    path('cancelar/<int:pk>/', views.cancelar_notificacion_programada, name='cancelar_notificacion_programada'),
]
