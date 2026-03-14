from django.urls import path
from . import views
from django.contrib.auth.views import LogoutView
from django.shortcuts import render
from django.contrib.auth import views as auth_views

urlpatterns = [

    path('aportacion/<int:idAportacion>/pago/', views.pago_aportacion, name='pago_aportacion'),

    path('api/actividad/<int:idActividad>/', views.actividad_detalles_api, name='actividad_detalles_api'),

    path('aportacion/<int:idAportacion>/paypal/', views.paypal_payment_aportacion, name='paypal_payment_aportacion'),
    path('aportacion/<int:idAportacion>/stripe/', views.stripe_payment_aportacion, name='stripe_payment_aportacion'),

    path('aportacion/<int:idAportacion>/exitoso/', views.pago_exitoso_aportacion, name='pago_exitoso_aportacion'),
    path('aportacion/<int:aportacion_id>/pendiente/', views.pago_pendiente_aportacion, name='pago_pendiente_aportacion'),

    path('pago/cancelado/', views.pago_cancelado, name='pago_cancelado'),

    path('', views.index, name='index'),
    path('privacidad/', views.privacidad, name='privacidad'),
    path('administracion/', views.administracion_redirect, name='administracion_redirect'),
    path('api/registrar-player-id/', views.registrar_player_id, name='registrar_player_id'),
    path("configuraciones/banner-principal/", views.banner_principal, name="banner_principal"),
    path('configuraciones/banners/<int:id>/editar/', views.editar_banner_principal, name='editar_banner_principal'),
    path('configuraciones/banners/<int:id>/alternar_estado/', views.alternar_estado_banner, name='alternar_estado_banner'),
    path('configuraciones/banners/eliminar/<int:id>/', views.eliminar_banner_principal, name='eliminar_banner_principal'),
    path('archivos/', views.gestionar_archivos, name='gestionar_archivos'),
    path('archivos/<int:id_archivo>/editar/', views.editar_archivo, name='editar_archivo'),
    path('archivos/<int:id_archivo>/eliminar/', views.eliminar_archivo, name='eliminar_archivo'),
    path('archivos/<int:id>/alternar_estado/', views.alternar_estado_archivo, name='alternar_estado_archivo_pagina'),
    path("configuraciones/configurar_pago_efectivo/", views.configurar_pago_efectivo, name="configurar_pago_efectivo"),
    path("mis-compras/", views.mis_compras, name="mis_compras"),
    path(
        "mis-compras/instrucciones-efectivo/<int:compra_id>/<str:formato>/",
        views.instrucciones_pago_efectivo,
        name="instrucciones_pago_efectivo",
    ),
    path("pago-pendiente/<int:compra_id>/", views.pago_pendiente, name="pago_pendiente"),
    path('acceso-restringido/', views.acceso_restringido, name='acceso_restringido'),
    path('login/', views.login_view, name='login'),
    path('logout/', LogoutView.as_view(next_page='/login/'), name='logout'),
    path('registro/', views.registro_no_socio, name='registro'),
    path('verificacion-pendiente/', lambda request: render(request, 'web/verificacion_pendiente.html'), name='verificacion_pendiente'),
    path('verificacion-pendiente/', views.reenviar_verificacion, name='reenviar_verificacion'),
    path('verificar-email/<uuid:token>/', views.verificar_email, name='verificar_email'),
    path('perfil/', views.perfil_view, name='perfil'),
    path('descargar_gafete/', views.descargar_gafete, name='descargar_gafete'),
    path('reenviar-verificacion/', views.reenviar_verificacion, name='reenviar_verificacion'),
    path('<int:idEvento>/detalles_evento/', views.evento_detalles, name='evento_detalles'),
    path('<int:idExpositor>/detalles_expositor/', views.expositor_detalles, name='expositor_detalles'),
    path('<int:idPatrocinador>/detalles_patrocinador/', views.patrocinador_detalles, name='patrocinador_detalles'),
    path('<int:idEvento>/stands/', views.stands, name='stands'),
    path('<int:idStand>/detalles_stand/', views.stand, name='stand_detalles'),
    path('<int:idEntrada>/pago_entrada/', views.pago_entrada, name='pago_entrada'),
    path('paypal/<int:idEntrada>/<int:compra_id>/', views.paypal_payment, name='paypal_payment'),
    path('stripe/<int:idEntrada>/<int:compra_id>/', views.stripe_payment, name='stripe_payment'),
    path('openpay/<int:idEntrada>/<int:compra_id>/', views.openpay_payment, name='openpay_payment'),
    path('pago-exitoso/<int:idEntrada>/<str:metodo_pago>/<int:compra_id>/', views.pago_exitoso, name='pago_exitoso'),
    path("pago_cancelado/", views.pago_cancelado, name="pago_cancelado"),
    path('<int:idEntrada>/registro_gratuito/', views.registro_gratuito, name='registro_gratuito'),
    path('<int:idEvento>/registro_gratuito_evento/', views.registro_gratuito_evento, name='registro_gratuito_evento'),
    path("pago_actividad/<int:idActividad>/", views.pago_actividad, name="pago_actividad"),
    path("registro_gratuito_actividad/<int:idActividad>/", views.registro_gratuito_actividad, name="registro_gratuito_actividad"),
    path("registro_acompañantes_actividad/<int:idActividad>/", views.registro_acompañantes_actividad, name="registro_acompañantes_actividad"),

    path("paypal_payment_actividad/<int:idActividad>/", views.paypal_payment_actividad, name="paypal_payment_actividad"),
    path("stripe_payment_actividad/<int:idActividad>/", views.stripe_payment_actividad, name="stripe_payment_actividad"),
    path("openpay_payment_actividad/<int:idActividad>/", views.openpay_payment_actividad, name="openpay_payment_actividad"),

    path("pago_exitoso_actividad/<int:idActividad>/<str:metodo_pago>/", views.pago_exitoso_actividad, name="pago_exitoso_actividad"),
    path('actividad/<int:idActividad>/editar-acompañantes/', views.editar_acompañantes, name='editar_acompañantes'),
    path("solicitar-cita/", views.solicitar_cita, name="solicitar_cita"),

    path("cita/<int:idCita>/pago/", views.pago_cita, name="pago_cita"),

    path("cita/<int:idCita>/paypal/", views.paypal_payment_cita, name="paypal_payment_cita"),
    path("cita/<int:idCita>/stripe/", views.stripe_payment_cita, name="stripe_payment_cita"),
    path("cita/<int:idCita>/openpay/", views.openpay_payment_cita, name="openpay_payment_cita"),

    path("cita/<int:idCita>/pago/exitoso/<str:metodo_pago>/", views.pago_exitoso_cita, name="pago_exitoso_cita"),
    path("cita/pago/cancelado/", views.pago_cancelado, name="pago_cancelado"),
    path('registro-por-cupon/<int:idEntrada>/<int:compra_id>/', views.registro_por_cupon, name='registro_por_cupon'),

    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='web/password_reset.html',
        email_template_name='web/password_reset_email.html',
        subject_template_name='web/password_reset_subject.txt',
        success_url='/password-reset/enviado/'
    ), name='password_reset'),

    path('password-reset/enviado/', auth_views.PasswordResetDoneView.as_view(
        template_name='web/password_reset_done.html'
    ), name='password_reset_done'),

    path('password-reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='web/password_reset_confirm.html',
        success_url='/password-reset/completo/'
    ), name='password_reset_confirm'),

    path('password-reset/completo/', auth_views.PasswordResetCompleteView.as_view(
        template_name='web/password_reset_complete.html'
    ), name='password_reset_complete'),

]
