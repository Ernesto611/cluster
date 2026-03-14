from django.urls import path
from . import views

urlpatterns = [
    path('chat/message/', views.ChatMessageView.as_view(), name='chat_message'),
    path('chatbot/config/', views.chatbot_config_view, name='chatbot_config'),
    path('chatbot/documentos/', views.chatbot_documentos_view, name='chatbot_documentos'),
    path('chatbot/documentos/<int:documento_id>/editar/', views.editar_documento_chatbot, name='editar_documento_chatbot'),
    path('chatbot/documentos/<int:documento_id>/alternar-estado/', views.alternar_estado_documento_chatbot, name='alternar_estado_documento_chatbot'),
    path('chatbot/documentos/<int:documento_id>/eliminar/', views.eliminar_documento_chatbot, name='eliminar_documento_chatbot'),
]
