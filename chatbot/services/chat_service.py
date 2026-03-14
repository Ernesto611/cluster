import os
import unicodedata
import locale
from dotenv import load_dotenv
from utils.chatbox import cargar_documentos_chatbox
from utils.fechas import ahora_mx
from django.urls import reverse
from chatbot.models import ChatbotConfig
from eventos.models import Evento
from actividades.models import Actividad
from expositores.models import Expositor
from patrocinadores.models import Patrocinador
from stands.models import Stand
from entradas.models import Entrada
import re

def formatear_respuesta_ia(texto):

    texto = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", texto)
    texto = re.sub(r"\*(.+?)\*", r"<em>\1</em>", texto)
    texto = re.sub(
        r"(https?://[^\s]+)",
        r"<a href='\1' style='color: #007bff; text-decoration: underline;'>\1</a>",
        texto
    )
    return texto.replace("\n", "<br>")

load_dotenv()

USE_GROQ = os.getenv("USE_GROQ", "true").lower() == "true"

try:
    if USE_GROQ:
        from groq import Groq
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
             print("⚠️ GROQ_API_KEY no encontrada.")
             client = None
        else:
            client = Groq(api_key=api_key)
        MODEL = "llama3-70b-8192"
    else:
        from openai import OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("⚠️ OPENAI_API_KEY no encontrada.")
            client = None
        else:
            client = OpenAI(api_key=api_key)
        MODEL = "gpt-4o"
except Exception as e:
    print(f"⚠️ Error inicializando cliente de IA: {e}")
    client = None

try:
    locale.setlocale(locale.LC_TIME, 'es_MX.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_TIME, 'Spanish_Mexico.1252')
    except locale.Error:
        print("⚠️ No se pudo establecer locale español.")

ultimo_evento_consultado = None

def normalizar_texto(texto):
    return ''.join(
        c for c in unicodedata.normalize('NFD', texto.lower())
        if unicodedata.category(c) != 'Mn'
    )

def get_prompt_base():
    config = ChatbotConfig.objects.first()
    prompt_base = config.generar_prompt_completo() if config else (
        "Eres un asistente virtual especializado en RegistroClustertim. "
        "Ayudas a los usuarios con dudas sobre el portal, registro y eventos."
    )
    documentos_contexto = cargar_documentos_chatbox()
    return f"{prompt_base}\n\n{documentos_contexto}".strip()

def build_absolute_url(request, relative_path):
    return request.build_absolute_uri(relative_path)

def responder_chatbox(request, user_message):

    global ultimo_evento_consultado
    user_message_norm = normalizar_texto(user_message)

    if any(palabra in user_message_norm for palabra in [
        "proximos eventos", "que eventos hay", "eventos disponibles"
    ]):
        eventos = Evento.objects.filter(fFechaInicio__gte=ahora_mx(), lActivo=True).order_by("fFechaInicio")[:5]
        if eventos.exists():
            respuesta = "📅 <strong>Estos son los próximos eventos:</strong><br><br>"
            for evento in eventos:
                url = build_absolute_url(request, reverse('evento_detalles', args=[evento.idEvento]))
                fecha_es = evento.fFechaInicio.strftime('%d de %B').capitalize()
                respuesta += (
                    f"📅 <strong>{fecha_es}</strong> – "
                    f"<em>{evento.aNombre}</em><br>"
                    f"👉 <a href='{url}' style='color: #007bff; text-decoration: underline;'>Ver detalles aquí</a><br><br>"
                )
            _guardar_historial_chat(request, "assistant", respuesta)
            return respuesta
        else:
            texto = "📅 No hay eventos próximos programados en este momento."
            _guardar_historial_chat(request, "assistant", texto)
            return texto

    frases_proximo_desayuno = [
        "proximo desayuno",
        "siguiente desayuno",
        "desayuno mas cercano",
        "desayuno cercano",
        "cual es el proximo desayuno",
        "cuando es el proximo desayuno",
        "que desayuno sigue",
        "que desayuno viene",
        "cual es el siguiente desayuno",
        "cuando es el siguiente desayuno",

        "proximos desayunos",
        "siguientes desayunos",
        "hay algun desayuno",
        "hay desayunos",
    ]

    if any(frase in user_message_norm for frase in frases_proximo_desayuno):
        evento = (Evento.objects
                  .filter(
                      fFechaInicio__gte=ahora_mx(),
                      lActivo=True,
                      categoria__idCategoria=1
                  )
                  .order_by("fFechaInicio")
                  .first())
        if evento:
            ultimo_evento_consultado = evento
            url = build_absolute_url(request, reverse('evento_detalles', args=[evento.idEvento]))
            fecha_es = evento.fFechaInicio.strftime('%d de %B').capitalize()
            respuesta = (
                f"🥐 El próximo desayuno es <strong>{evento.aNombre}</strong>, "
                f"el cual inicia el <strong>{fecha_es}</strong>.<br><br>"
                f"👉 <a href='{url}' style='color: #007bff; text-decoration: underline;'>Ver detalles aquí</a>"
            )
            _guardar_historial_chat(request, "assistant", respuesta)
            return respuesta
        else:
            texto = "🥐 No hay desayunos tecnológicos próximos programados en este momento."
            _guardar_historial_chat(request, "assistant", texto)
            return texto

    frases_proximo_curso = [
        "proximo curso",
        "siguiente curso",
        "curso mas cercano",
        "curso cercano",
        "cual es el proximo curso",
        "cuando es el proximo curso",
        "que curso sigue",
        "que curso viene",
        "cual es el siguiente curso",
        "cuando es el siguiente curso",

        "proxima certificacion",
        "siguiente certificacion",
        "cual es la proxima certificacion",
        "cuando es la proxima certificacion",
        "hay alguna certificacion",

        "proximos cursos",
        "siguientes cursos",
        "hay cursos",
        "hay certificaciones",
        "cursos y certificaciones",
    ]

    if any(frase in user_message_norm for frase in frases_proximo_curso):
        evento = (Evento.objects
                  .filter(
                      fFechaInicio__gte=ahora_mx(),
                      lActivo=True,
                      categoria__idCategoria=2
                  )
                  .order_by("fFechaInicio")
                  .first())
        if evento:
            ultimo_evento_consultado = evento
            url = build_absolute_url(request, reverse('evento_detalles', args=[evento.idEvento]))
            fecha_es = evento.fFechaInicio.strftime('%d de %B').capitalize()
            respuesta = (
                f"📘 El próximo curso/certificación es <strong>{evento.aNombre}</strong>, "
                f"el cual inicia el <strong>{fecha_es}</strong>.<br><br>"
                f"👉 <a href='{url}' style='color: #007bff; text-decoration: underline;'>Ver detalles aquí</a>"
            )
            _guardar_historial_chat(request, "assistant", respuesta)
            return respuesta
        else:
            texto = "📘 No hay cursos o certificaciones próximos programados en este momento."
            _guardar_historial_chat(request, "assistant", texto)
            return texto

    frases_proximo_evento = [
        "proximo evento",
        "siguiente evento",
        "evento mas cercano",
        "evento cercano",
        "cual es el proximo evento",
        "cuando es el proximo evento",
        "que evento sigue",
        "que evento viene",
        "cual es el siguiente evento",
        "cuando es el siguiente evento",
    ]

    if any(frase in user_message_norm for frase in frases_proximo_evento):
        evento = (Evento.objects
                  .filter(fFechaInicio__gte=ahora_mx(), lActivo=True)
                  .order_by("fFechaInicio")
                  .first())
        if evento:
            ultimo_evento_consultado = evento
            url = build_absolute_url(request, reverse('evento_detalles', args=[evento.idEvento]))

            fecha_es = evento.fFechaInicio.strftime('%d de %B').capitalize()
            respuesta = (
                f"📌 El próximo evento es <strong>{evento.aNombre}</strong>, "
                f"el cual inicia el <strong>{fecha_es}</strong>.<br><br>"
                f"👉 <a href='{url}' style='color: #007bff; text-decoration: underline;'>Ver detalles aquí</a>"
            )
            _guardar_historial_chat(request, "assistant", respuesta)
            return respuesta
        else:
            texto = "📅 No hay eventos próximos programados en este momento."
            _guardar_historial_chat(request, "assistant", texto)
            return texto

    for evento in Evento.objects.filter(lActivo=True):
        nombre_evento_norm = normalizar_texto(evento.aNombre)

        if nombre_evento_norm in user_message_norm:
            ultimo_evento_consultado = evento
            url = build_absolute_url(request, reverse('evento_detalles', args=[evento.idEvento]))
            respuesta = (
                f"📖 <strong>{evento.aNombre}</strong><br>"
                f"{evento.aDescripcion}<br><br>"
                f"👉 <a href='{url}' style='color: #007bff; text-decoration: underline;'>Ver detalles aquí</a>"
            )
            _guardar_historial_chat(request, "assistant", respuesta)
            return respuesta

    if ultimo_evento_consultado:
        e = ultimo_evento_consultado
        if any(p in user_message_norm for p in ["cuando", "fecha", "hora", "horario"]):
            fecha_inicio = e.fFechaInicio.strftime('%d/%m/%Y %H:%M')
            fecha_fin = e.fFechaFin.strftime('%d/%m/%Y %H:%M')
            respuesta = (
                f"🕒 El evento <strong>{e.aNombre}</strong> inicia el <strong>{fecha_inicio}</strong> "
                f"y termina el <strong>{fecha_fin}</strong>."
            )
            _guardar_historial_chat(request, "assistant", respuesta)
            return respuesta

    system_prompt = get_prompt_base()
    historial = _obtener_historial_chat(request)
    historial.append({"role": "user", "content": user_message})

    if USE_GROQ:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "system", "content": system_prompt}] + historial[-10:],
            temperature=0.3,
            max_tokens=500
        )
        texto_ia = response.choices[0].message.content
    else:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "system", "content": system_prompt}] + historial[-10:],
            temperature=0.3,
            max_tokens=500
        )
        texto_ia = response.choices[0].message.content

    texto_formateado = formatear_respuesta_ia(texto_ia)
    _guardar_historial_chat(request, "assistant", texto_formateado)
    return texto_formateado

def _obtener_historial_chat(request):

    if "chat_history" not in request.session:
        request.session["chat_history"] = []
    return request.session["chat_history"]

def _guardar_historial_chat(request, role, content):

    history = _obtener_historial_chat(request)
    history.append({"role": role, "content": content})

    request.session["chat_history"] = history[-20:]
    request.session.modified = True

get_chat_response = responder_chatbox
