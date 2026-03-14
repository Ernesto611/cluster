from django.urls import path
from . import views

urlpatterns = [
    path('listado/', views.listado, name='listado_stands'),
    path('citas/', views.listado_citas, name='listado_citas'),
    path('agregar/', views.agregar, name='agregar_stand'),
    path('<int:idStand>/alternar_estado/', views.alternar_estado, name='alternar_estado_stand'),
    path('<int:idStand>/detalles/', views.detalles, name='detalles_stand'),
    path('<int:idStand>/editar/', views.editar, name='editar_stand'),
    path('<int:idStand>/eliminar/', views.eliminar, name='eliminar_stand'),
    path('ajax/stands-por-evento/', views.obtener_stands_por_evento, name='ajax_stands_por_evento'),
    path('registros/', views.listar_registros_stands, name='listar_registros_stands'),
    path('productos/<int:idStand>/', views.listado_productos, name='listado_productos'),
    path('productos/agregar/<int:idStand>/', views.agregar_producto, name='agregar_producto'),
    path('productos/detalles/<int:idProducto>/', views.detalles_producto, name='detalles_producto'),
    path('productos/editar/<int:idProducto>/', views.editar_producto, name='editar_producto'),
    path('productos/eliminar/<int:idProducto>/', views.eliminar_producto, name='eliminar_producto'),
    path('productos/alternar_estado/<int:idProducto>/', views.alternar_estado_producto, name='alternar_estado_producto'),
    path("citas/detalles/<int:idCita>/", views.detalles_cita, name="detalles_cita"),
    path("citas/horarios/", views.gestionar_horarios_citas, name="gestionar_horarios_citas"),
    path('archivos/<int:idStand>/', views.gestionar_archivos_stand, name='gestionar_archivos_stand'),
    path('archivos/<int:id_archivo>/editar/', views.editar_archivo_stand, name='editar_archivo_stand'),
    path('archivos/<int:id_archivo>/eliminar/', views.eliminar_archivo_stand, name='eliminar_archivo_stand'),
    path('archivos/<int:id>/alternar_estado/', views.alternar_estado_archivo, name='alternar_estado_archivo_stand'),
]
