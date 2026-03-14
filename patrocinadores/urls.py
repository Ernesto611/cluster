from django.urls import path
from . import views

urlpatterns = [
    path('listado/', views.listado, name='listado_patrocinadores'),
    path('agregar/', views.agregar, name='agregar_patrocinador'),
    path('<int:idPatrocinador>/editar/', views.editar, name='editar_patrocinador'),
    path('<int:idPatrocinador>/eliminar/', views.eliminar, name='eliminar_patrocinador'),
    path('<int:idPatrocinador>/alternar_estado/', views.alternar_estado, name='alternar_estado_patrocinador'),
]
