from django.urls import path
from . import views

urlpatterns = [

    path('escaneo-evento/', views.escaneo_evento, name='escaneo_evento'),
    path('escaneo-actividad/', views.escaneo_actividad, name='escaneo_actividad'),
    path('entrada_registrada/<int:idUsuario>/<int:idEvento>/', views.entrada_registrada, name='entrada_registrada'),
    path('ya_registrado/<int:idUsuario>/<int:idEvento>/', views.ya_registrado, name='ya_registrado'),
    path('no_tiene_entrada/<int:idUsuario>/<int:idEvento>/', views.no_tiene_entrada, name='no_tiene_entrada'),
    path('qr_no_valido/<str:tipo>/', views.qr_no_valido, name='qr_no_valido'),
    path('entrada_registrada_actividad/<int:idUsuario>/<int:idActividad>/', views.entrada_registrada_actividad, name='entrada_registrada_actividad'),
    path('ya_registrado_actividad/<int:idUsuario>/<int:idActividad>/', views.ya_registrado_actividad, name='ya_registrado_actividad'),
    path('no_tiene_entrada_actividad/<int:idUsuario>/<int:idActividad>/', views.no_tiene_entrada_actividad, name='no_tiene_entrada_actividad'),
    path('actividad_llena/<int:idUsuario>/<int:idActividad>/', views.actividad_llena, name='actividad_llena'),
    path('escaneo-stand/', views.escaneo_stand, name='escaneo_stand'),
    path('visita_registrada_stand/<int:idUsuario>/<int:idStand>/', views.visita_registrada_stand, name='visita_registrada_stand'),
    path('ya_visitado_stand/<int:idUsuario>/<int:idStand>/', views.ya_visitado_stand, name='ya_visitado_stand'),

    path('listado/', views.listar_administradores, name='listar_administradores'),
    path('detalles/<int:idUsuario>/', views.detalles_usuario, name='detalles_usuario'),
    path('administradores/agregar/', views.agregar_administrador, name='agregar_administrador'),
    path('administradores/editar/<int:idUsuario>/', views.editar_administrador, name='editar_administrador'),
    path('administradores/permisos/<int:idUsuario>/', views.asignar_permisos_usuario, name='asignar_permisos_usuario'),
    path('eliminar/<int:idUsuario>/', views.eliminar_usuario, name='eliminar_usuario'),
    path('alternar_estado/<int:idUsuario>/', views.alternar_estado_usuario, name='alternar_estado_usuario'),
    path('gestores/', views.listar_gestores, name='listar_gestores'),
    path('gestores/agregar/', views.agregar_gestor, name='agregar_gestor'),
    path('gestores/editar/<int:idUsuario>/', views.editar_gestor, name='editar_gestor'),

    path('clientes/', views.listar_clientes, name='listar_clientes'),

    path('configuracion_descargas/', views.configurar_exportacion, name='configurar_exportacion'),
    path('exportar/eventos/', views.descargar_excel_eventos, name='descargar_excel_eventos'),
    path('exportar/actividades/', views.descargar_excel_actividades, name='descargar_excel_actividades'),
    path('exportar/stands/', views.descargar_excel_stands, name='descargar_excel_stands'),

]
