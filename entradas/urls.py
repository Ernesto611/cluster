from django.urls import path
from . import views

urlpatterns = [
    path('listado/', views.listado, name='listado_entradas'),
    path('agregar/', views.agregar, name='agregar_entrada'),
    path('<int:idEntrada>/alternar-estado/', views.alternar_estado_entrada, name='alternar_estado_entrada'),
    path('<int:evento_id>/actividades/', views.obtener_actividades, name='obtener_actividades'),
    path('<int:idEntrada>/editar/', views.editar_entrada, name='editar_entrada'),
    path('<int:idEntrada>/detalles/', views.detalles_entrada, name='detalles_entrada'),
    path('<int:idEntrada>/eliminar/', views.eliminar_entrada, name='eliminar_entrada'),
    path('registros/', views.listar_compras_entradas, name='listar_compras_entradas'),
    path('cupones/agregar/<int:idEntrada>/', views.agregar_cupon, name='agregar_cupon'),
    path('cupones/<int:idEntrada>/', views.listar_cupones, name='listar_cupones'),
    path('cupones/<int:id>/editar/', views.editar_cupon, name='editar_cupon'),
    path('cupones/<int:id>/alternar_estado/', views.alternar_estado_cupon, name='alternar_estado_cupon'),
    path('efectivo/', views.listado_compras_efectivo, name='listado_compras_efectivo'),
    path('efectivo/<int:compra_id>/pagar/', views.marcar_pago_efectivo, name='marcar_pago_efectivo'),
]
