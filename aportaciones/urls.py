from django.urls import path
from . import views

urlpatterns = [
    path('aportadores/', views.listado_aportadores, name='listado_aportadores'),
    path('aportadores/agregar/', views.agregar_aportador, name='agregar_aportador'),
    path('aportadores/editar/<int:idAportador>/', views.editar_aportador, name='editar_aportador'),
    path('aportadores/alternar-estado/<int:idAportador>/', views.alternar_estado_aportador, name='alternar_estado_aportador'),
    path('', views.listado_aportaciones, name='listado_aportaciones'),
    path('agregar/', views.agregar_aportacion, name='agregar_aportacion'),
    path('editar/<int:idAportacion>/', views.editar_aportacion, name='editar_aportacion'),
    path('marcar-como-pagada/<int:idAportacion>/', views.marcar_como_pagada, name='marcar_como_pagada'),
]
