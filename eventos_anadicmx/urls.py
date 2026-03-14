from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from paypal.standard.ipn import views as paypal_views
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('web.urls')),
    path('usuarios/', include('usuarios.urls')),
    path('eventos/', include('eventos.urls')),
    path('actividades/', include('actividades.urls')),
    path('agendas/', include('agendas.urls')),
    path('expositores/', include('expositores.urls')),
    path('stands/', include('stands.urls')),
    path('patrocinadores/', include('patrocinadores.urls')),
    path('entradas/', include('entradas.urls')),
    path('notificaciones/', include('notificaciones.urls')),
    path('aportaciones/', include('aportaciones.urls')),
    path("api/", include("chatbot.urls")),
    path('paypal/', include('paypal.standard.ipn.urls')),
    path('', include('pwa.urls')),
    path('accounts/', include('allauth.urls')),
    path('OneSignalSDKWorker.js', TemplateView.as_view(template_name='OneSignalSDKWorker.js', content_type='application/javascript')),
    path('OneSignalSDKUpdaterWorker.js', TemplateView.as_view(template_name='OneSignalSDKUpdaterWorker.js', content_type='application/javascript')),
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
