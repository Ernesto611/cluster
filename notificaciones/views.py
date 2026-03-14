from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Notificacion
from .forms import NotificacionForm
from django.db.models import Q
import json
import requests
from django.conf import settings
from django.utils import timezone
from datetime import datetime
from usuarios.models import Usuario, OneSignalPlayer
from zoneinfo import ZoneInfo
from utils.fechas import ahora_mx
from eventos.models import RegistroEvento
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.core.mail import EmailMultiAlternatives

@login_required
def listado_notificaciones(request):

    if request.user.tipo_usuario == 'super_administrador':
        notificaciones = Notificacion.objects.all()
    else:
        notificaciones = Notificacion.objects.filter(creado_por=request.user)

    q = request.GET.get('q')
    estado = request.GET.get('estado')

    if q:
        notificaciones = notificaciones.filter(
            Q(titulo__icontains=q) |
            Q(mensaje__icontains=q)
        )

    if estado:
        notificaciones = notificaciones.filter(estado=estado)

    context = {
        'notificaciones': notificaciones,
        'q': q,
        'estado': estado
    }
    return render(request, 'notificaciones/listado.html', context)

@login_required
def agregar_notificacion(request):

    if request.method == 'POST':
        form = NotificacionForm(request.POST, request.FILES)
        if form.is_valid():
            notificacion = form.save(commit=False)
            notificacion.creado_por = request.user
            notificacion.estado = 'borrador'
            notificacion.save()
            messages.success(request, 'Notificación creada exitosamente')
            return redirect('listado_notificaciones')
    else:
        form = NotificacionForm()

    context = {
        'form': form
    }
    return render(request, 'notificaciones/agregar.html', context)

@login_required
def editar_notificacion(request, pk):

    notificacion = get_object_or_404(Notificacion, pk=pk)

    if request.user.tipo_usuario != 'super_administrador' and notificacion.creado_por != request.user:
        messages.error(request, 'No tienes permiso para editar esta notificación')
        return redirect('listado_notificaciones')

    if request.method == 'POST':
        form = NotificacionForm(request.POST, request.FILES, instance=notificacion)
        if form.is_valid():
            form.save()
            messages.success(request, 'Notificación actualizada exitosamente')
            return redirect('listado_notificaciones')
    else:
        form = NotificacionForm(instance=notificacion)

    context = {
        'form': form,
        'notificacion': notificacion
    }
    return render(request, 'notificaciones/editar.html', context)

def obtener_emails_destinatarios(clave_destinatarios):
    qs = (Usuario.objects
          .filter(is_active=True)
          .exclude(email__isnull=True)
          .exclude(email=""))

    if clave_destinatarios == "todos":
        pass

    elif clave_destinatarios == "clientes":
        qs = qs.filter(tipo_usuario="cliente")

    elif clave_destinatarios == "administradores":
        qs = qs.filter(tipo_usuario__in=["administrador", "super_administrador"])

    elif clave_destinatarios == "desayunos":
        usuarios_ids = (RegistroEvento.objects
                        .filter(evento__categoria__idCategoria=ID_CATEGORIA_DESAYUNOS)
                        .values_list('usuario_id', flat=True)
                        .distinct())
        qs = qs.filter(pk__in=usuarios_ids).distinct()

    elif clave_destinatarios == "cursos":
        usuarios_ids = (RegistroEvento.objects
                        .filter(evento__categoria__idCategoria=ID_CATEGORIA_CURSOS)
                        .values_list('usuario_id', flat=True)
                        .distinct())
        qs = qs.filter(pk__in=usuarios_ids).distinct()

    else:
        qs = qs.none()

    emails = list(qs.values_list("email", flat=True))
    emails = sorted({e.strip().lower() for e in emails if e and e.strip()})

    return emails

def enviar_correo_notificacion(notificacion, emails, *, from_email=None, batch_size=80):
    if not emails:
        return 0

    emails = sorted({e.strip().lower() for e in emails if e and e.strip()})

    from_email = from_email or getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@registroclustertim.com")

    html_content = render_to_string("notificaciones/email_notificacion.html", {"notificacion": notificacion})
    text_content = strip_tags(html_content)
    asunto = notificacion.titulo

    enviados = 0
    for i in range(0, len(emails), batch_size):
        lote = emails[i:i+batch_size]
        msg = EmailMultiAlternatives(asunto, text_content, from_email, [from_email], bcc=lote)
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        enviados += len(lote)

    return enviados

@login_required
def enviar_notificacion(request, pk):
    notificacion = get_object_or_404(Notificacion, pk=pk)

    if request.user.tipo_usuario != 'super_administrador' and notificacion.creado_por != request.user:
        messages.error(request, 'No tienes permiso para enviar esta notificación')
        return redirect('listado_notificaciones')

    if request.method == 'POST':
        destinatarios = request.POST.get('destinatarios')
        fecha_programada = request.POST.get('fecha_programada')
        modo_envio = request.POST.get('modo_envio', 'push')

        if not destinatarios:
            messages.error(request, 'Debes seleccionar los destinatarios')
            return render(request, 'notificaciones/enviar.html', {'notificacion': notificacion})

        fecha_envio = None
        if fecha_programada:
            try:
                fecha_envio = datetime.fromisoformat(fecha_programada)
                fecha_envio = fecha_envio.replace(tzinfo=ZoneInfo("America/Mexico_City"))
            except ValueError:
                messages.error(request, 'Formato de fecha inválido')
                return render(request, 'notificaciones/enviar.html', {'notificacion': notificacion})

        try:
            if modo_envio == 'push':
                player_ids = obtener_player_ids(destinatarios)
                if not player_ids:
                    messages.error(request, 'No se encontraron usuarios para enviar la notificación')
                    return render(request, 'notificaciones/enviar.html', {'notificacion': notificacion})

                if fecha_envio and fecha_envio > ahora_mx():
                    resultado = enviar_notificacion_onesignal(notificacion, player_ids, fecha_envio)
                    notificacion.estado = 'programada'
                    notificacion.fecha_programada = fecha_envio.replace(tzinfo=None)
                    messages.success(request, f'Notificación push programada para {len(player_ids)} usuarios')
                else:
                    resultado = enviar_notificacion_onesignal(notificacion, player_ids)
                    notificacion.estado = 'enviada'
                    messages.success(request, f'Notificación push enviada a {len(player_ids)} usuarios')

                notificacion.save()
                if resultado and isinstance(resultado, dict) and 'id' in resultado:
                    notificacion.datos_adicionales = notificacion.datos_adicionales or {}
                    notificacion.datos_adicionales['onesignal_id'] = resultado['id']
                    notificacion.save()

            else:
                emails = obtener_emails_destinatarios(destinatarios)
                if not emails:
                    messages.error(request, 'No se encontraron correos de destinatarios para enviar el email')
                    return render(request, 'notificaciones/enviar.html', {'notificacion': notificacion})

                enviados = enviar_correo_notificacion(notificacion, emails)

                notificacion.datos_adicionales = notificacion.datos_adicionales or {}
                notificacion.datos_adicionales['ultimo_envio_email'] = ahora_mx().isoformat()
                notificacion.estado = 'enviada'
                notificacion.save()

                messages.success(request, f'Email enviado a {enviados} destinatarios')

        except Exception as e:
            messages.error(request, f'Error al procesar el envío: {str(e)}')
            return render(request, 'notificaciones/enviar.html', {'notificacion': notificacion})

        return redirect('listado_notificaciones')

    context = {
        'notificacion': notificacion
    }
    return render(request, 'notificaciones/enviar.html', context)

ID_CATEGORIA_DESAYUNOS = 1
ID_CATEGORIA_CURSOS = 2

def obtener_player_ids(tipo_destinatarios):

    qs_players = OneSignalPlayer.objects.all()

    if tipo_destinatarios == 'todos':
        player_ids = qs_players.values_list('player_id', flat=True).distinct()

    elif tipo_destinatarios == 'clientes':
        player_ids = qs_players.filter(
            usuario__tipo_usuario='cliente'
        ).values_list('player_id', flat=True).distinct()

    elif tipo_destinatarios == 'administradores':
        player_ids = qs_players.filter(
            usuario__tipo_usuario='administrador'
        ).values_list('player_id', flat=True).distinct()

    elif tipo_destinatarios == 'desayunos':
        usuarios_ids = RegistroEvento.objects.filter(
            evento__categoria__idCategoria=ID_CATEGORIA_DESAYUNOS
        ).values_list('usuario_idUsuario', flat=True).distinct()

        player_ids = qs_players.filter(
            usuario_id__in=usuarios_ids
        ).values_list('player_id', flat=True).distinct()

    elif tipo_destinatarios == 'cursos':
        usuarios_ids = RegistroEvento.objects.filter(
            evento__categoria__idCategoria=ID_CATEGORIA_CURSOS
        ).values_list('usuario_idUsuario', flat=True).distinct()

        player_ids = qs_players.filter(
            usuario_id__in=usuarios_ids
        ).values_list('player_id', flat=True).distinct()

    else:
        return []

    return list(player_ids)

def enviar_notificacion_onesignal(notificacion, player_ids, fecha_programada=None):

    from django.conf import settings
    import requests

    ONESIGNAL_APP_ID = getattr(settings, 'ONESIGNAL_APP_ID', '')
    ONESIGNAL_REST_API_KEY = getattr(settings, 'ONESIGNAL_REST_API_KEY', '')

    if not ONESIGNAL_APP_ID or not ONESIGNAL_REST_API_KEY:
        raise Exception('Configuración de OneSignal incompleta')

    payload = {
        "app_id": ONESIGNAL_APP_ID,
        "include_player_ids": player_ids,
        "headings": {
            "en": notificacion.titulo,
            "es": notificacion.titulo
        },
        "contents": {
            "en": notificacion.mensaje,
            "es": notificacion.mensaje
        }
    }

    if notificacion.imagen:
        base_url = "https://registroclustertim.com"
        image_url = f"{base_url}{notificacion.imagen.url}"

        payload["big_picture"] = image_url

        payload["chrome_web_image"] = image_url

        payload["ios_attachments"] = {"id": image_url}

        payload["large_icon"] = image_url

    if notificacion.datos_adicionales:
        payload["data"] = notificacion.datos_adicionales

    if fecha_programada:
        timestamp = int(fecha_programada.timestamp())
        payload["send_after"] = timestamp

    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Authorization": f"Basic {ONESIGNAL_REST_API_KEY}"
    }

    response = requests.post(
        "https://onesignal.com/api/v1/notifications",
        headers=headers,
        json=payload
    )

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f'Error de OneSignal: {response.status_code} - {response.text}')

@login_required
def cancelar_notificacion_programada(request, pk):

    notificacion = get_object_or_404(Notificacion, pk=pk)

    if request.user.tipo_usuario != 'super_administrador' and notificacion.creado_por != request.user:
        messages.error(request, 'No tienes permiso para cancelar esta notificación')
        return redirect('listado_notificaciones')

    if notificacion.estado != 'programada':
        messages.error(request, 'Esta notificación no está programada')
        return redirect('listado_notificaciones')

    onesignal_id = notificacion.datos_adicionales.get('onesignal_id')
    if not onesignal_id:
        messages.error(request, 'No se encontró el ID de OneSignal para cancelar')
        return redirect('listado_notificaciones')

    try:

        ONESIGNAL_REST_API_KEY = getattr(settings, 'ONESIGNAL_REST_API_KEY', '')
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": f"Basic {ONESIGNAL_REST_API_KEY}"
        }

        response = requests.delete(
            f"https://onesignal.com/api/v1/notifications/{onesignal_id}",
            headers=headers
        )

        if response.status_code == 200:
            notificacion.estado = 'borrador'
            notificacion.fecha_programada = None
            notificacion.save()
            messages.success(request, 'Notificación cancelada exitosamente')
        else:
            messages.error(request, f'Error al cancelar la notificación: {response.text}')

    except Exception as e:
        messages.error(request, f'Error al cancelar la notificación: {str(e)}')

    return redirect('listado_notificaciones')
