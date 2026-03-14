from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .services.chat_service import get_chat_response, USE_GROQ
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
import json
import logging
from django.utils import timezone
import tempfile
import speech_recognition as sr
from pydub import AudioSegment
import traceback
from pydub.utils import which
from django.conf import settings
from django.utils.html import escape
from .models import ChatbotConfig, ChatbotDocumento, SesionConversacion, ConversacionChatbot
from .forms import ChatbotConfigForm, ChatbotDocumentoForm
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
import os
import uuid

def sanitize_message(message):

    if len(message) > 500:
        raise ValueError("Mensaje demasiado largo")
    return escape(message.strip())

AudioSegment.converter = which("ffmpeg")
AudioSegment.ffprobe   = which("ffprobe")

if not USE_GROQ:
    from openai import OpenAI
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

logger = logging.getLogger(__name__)

QUICK_RESPONSES = {

}

from django.core.cache import cache

RATE_LIMIT_SECONDS = 10

class ChatMessageView(View):

    def post(self, request):
        try:
            client_ip = self.get_client_ip(request)
            if self.is_rate_limited(client_ip):
                return JsonResponse({
                    'error': 'Demasiadas solicitudes. Por favor espera unos segundos antes de volver a intentarlo.'
                }, status=429)

            message = sanitize_message(request.POST.get('message', ''))
            audio_file = request.FILES.get('audio')

            if not message and not audio_file:
                return JsonResponse({
                    'error': 'Mensaje o audio requerido'
                }, status=400)

            if message:
                logger.info(f"Mensaje recibido: {message}")
                response = self.get_quick_or_ai_response(message)

            elif audio_file:
                logger.info("Audio recibido, procesando...")
                response = self.process_audio_message(audio_file)

            self.save_chat_message(request.user, message, response)

            return JsonResponse({
                'success': True,
                'response': response,
                'timestamp': timezone.now().isoformat()
            })

        except Exception as e:
            logger.error("Error en chat:\n" + traceback.format_exc())
            return JsonResponse({
                'error': 'Error interno del servidor'
            }, status=500)

    def get_client_ip(self, request):

        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def is_rate_limited(self, ip):

        key = f"chat_rate_limit_{ip}"
        if cache.get(key):
            return True
        cache.set(key, "blocked", RATE_LIMIT_SECONDS)
        return False

    def get_quick_or_ai_response(self, message):

        message_lower = message.lower()
        for keyword, quick_response in QUICK_RESPONSES.items():
            if keyword in message_lower:
                logger.info(f"Respuesta rápida para: {keyword}")
                return quick_response

        logger.info("Sin coincidencias, llamando a IA...")
        return get_chat_response(self.request, message)

    def process_audio_message(self, audio_file):

        try:

            with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_audio:
                for chunk in audio_file.chunks():
                    temp_audio.write(chunk)
                temp_audio_path = temp_audio.name

            converted_wav_path = temp_audio_path.replace(".webm", ".wav")
            audio = AudioSegment.from_file(temp_audio_path)
            audio = audio.set_channels(1)
            audio = audio.set_frame_rate(16000)
            audio = audio + 5
            audio.export(converted_wav_path, format="wav")

            if USE_GROQ:

                recognizer = sr.Recognizer()
                with sr.AudioFile(converted_wav_path) as source:
                    audio_data = recognizer.record(source)
                    try:
                        transcription = recognizer.recognize_google(audio_data, language="es-ES")
                        logger.info(f"Transcripción local: {transcription}")
                        return self.get_quick_or_ai_response(transcription)
                    except sr.UnknownValueError:
                        logger.warning("No se pudo entender el audio.")
                        return "No pude entender el mensaje de voz. ¿Puedes intentarlo de nuevo hablando más claro?"
            else:

                logger.info("Transcribiendo con Whisper API...")
                whisper_response = openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=open(converted_wav_path, "rb"),
                    response_format="text",
                    language="es",
                    prompt="Responde exactamente lo que escuchas, no inventes palabras adicionales."
                )
                transcription = whisper_response.strip()
                print(f"Transcripción Whisper: {transcription}")

                if len(transcription) < 5 or transcription.lower() in ["gracias", "ok", "de acuerdo"]:
                    return "No pude entender bien tu mensaje de voz. ¿Puedes intentarlo de nuevo?"

                response = self.get_quick_or_ai_response(transcription)
                logger.info(f"Respuesta para audio (flujo normalizado): {response}")
                return response

        except Exception as e:
            logger.error("Error procesando audio:\n" + traceback.format_exc())
            return "Lo siento, ocurrió un error al procesar tu mensaje de voz."

    def get_or_create_chat_session(self, request):
        session_id = request.session.get('chat_session_id')

        if session_id:
            try:
                return SesionConversacion.objects.get(uuid=session_id)
            except SesionConversacion.DoesNotExist:
                pass

        nueva_sesion = SesionConversacion.objects.create(
            usuario=request.user if request.user.is_authenticated else None,
            uuid=str(uuid.uuid4())
        )
        request.session['chat_session_id'] = nueva_sesion.uuid
        return nueva_sesion

    def save_chat_message(self, user, message, response):
        sesion = self.get_or_create_chat_session(self.request)

        if message:
            ConversacionChatbot.objects.create(sesion=sesion, rol='user', mensaje=message)
        if response:
            ConversacionChatbot.objects.create(sesion=sesion, rol='assistant', mensaje=response)

@login_required
def chatbot_config_view(request):

    config, created = ChatbotConfig.objects.get_or_create(
        pk=1,
        defaults={
            'nombre': 'Configuración Principal del Chatbot'
        }
    )

    if request.method == 'POST':
        form = ChatbotConfigForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, 'Configuración del chatbot actualizada correctamente.')
            return redirect('chatbot_config')
        else:
            messages.error(request, 'Por favor corrige los errores del formulario.')
    else:
        form = ChatbotConfigForm(instance=config)

    context = {
        'form': form,
        'config': config,
        'prompt_completo': config.generar_prompt_completo()
    }

    return render(request, 'chatbot/config.html', context)

@login_required
def chatbot_documentos_view(request):

    if request.method == 'POST':
        form = ChatbotDocumentoForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Documento subido correctamente.')
            return redirect('chatbot_documentos')
        else:

            print("❌ Errores al validar el formulario de documento:")
            for field, errors in form.errors.items():
                for error in errors:
                    print(f" - {field}: {error}")

            messages.error(request, 'Error al subir el documento. Verifica los datos.')
    else:
        form = ChatbotDocumentoForm()

    documentos = ChatbotDocumento.objects.all().order_by('-fecha_subida')

    permisos = ['agregar', 'editar', 'desactivar', 'borrar']

    context = {
        'form': form,
        'documentos': documentos,
        'permisos': permisos,
    }

    return render(request, 'chatbot/documentos.html', context)

@login_required
@require_POST
def editar_documento_chatbot(request, documento_id):

    documento = get_object_or_404(ChatbotDocumento, id=documento_id)

    nuevo_nombre = request.POST.get('nombre', '').strip()

    if nuevo_nombre:
        documento.nombre = nuevo_nombre
        documento.save()
        messages.success(request, 'Nombre del documento actualizado correctamente.')
    else:
        messages.error(request, 'El nombre del documento no puede estar vacío.')

    return redirect('chatbot_documentos')

@login_required
@require_POST
def alternar_estado_documento_chatbot(request, documento_id):

    documento = get_object_or_404(ChatbotDocumento, id=documento_id)

    documento.activo = not documento.activo
    documento.save()

    estado = "activado" if documento.activo else "desactivado"
    messages.success(request, f'Documento {estado} correctamente.')

    return redirect('chatbot_documentos')

@login_required
@require_POST
def eliminar_documento_chatbot(request, documento_id):

    documento = get_object_or_404(ChatbotDocumento, id=documento_id)

    nombre_documento = documento.nombre

    if documento.archivo:
        documento.archivo.delete()

    documento.delete()

    messages.success(request, f'Documento "{nombre_documento}" eliminado correctamente.')

    return redirect('chatbot_documentos')
