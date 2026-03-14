from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.conf import settings
from django.core.paginator import Paginator
from django.core.mail import send_mail, EmailMultiAlternatives
from django.urls import reverse
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone
from django.http import HttpResponse
from constance import config
from datetime import datetime
from paypal.standard.forms import PayPalPaymentsForm
from reportlab.lib.pagesizes import portrait
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from PIL import Image, ImageDraw
from io import BytesIO
from .forms import RegistroNoSocioForm, ReenviarVerificacionForm, PerfilForm, BannerPrincipalForm, ArchivoPaginaForm, DatosPagoEfectivoForm
from actividades.models import Actividad, RegistroActividad, AcompañanteActividad
from agendas.models import Agenda, AgendaActividades
from entradas.models import Entrada, EntradaActividad, CompraEntrada, Cupon, CodigoEntrada
from eventos.models import Evento, RegistroEvento
from aportaciones.models import Aportacion, Aportador
from expositores.models import Expositor, ExpositorActividad
from patrocinadores.models import Patrocinador
from stands.models import Stand, CitaStand, HorarioCita, ArchivoStand
from usuarios.models import Usuario, generar_qr_string
import qrcode
import base64
import stripe
import string
import random
import urllib.parse
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.dateparse import parse_datetime
from django.utils.timezone import now
import pprint
from django.utils.timezone import localtime
import os
from .models import BannerPrincipal, ArchivoPagina, DatosPagoEfectivoConfiguracion
from usuarios.decorators import role_required
import uuid
from django.core.files.base import ContentFile
from django.views.decorators.http import require_POST
from eventos.models import RegistroEvento
from actividades.models import RegistroActividad
from datetime import timedelta
from utils.fechas import ahora_mx
from django.db.models import Q
from utils.permisos import (
    permiso_o_superadmin_requerido,
    permiso_listado,
    permisos_de_usuario,
    tiene_permiso_en_alguna_categoria,
)
from usuarios.models import OneSignalPlayer
import json

from django.views.decorators.http import require_GET
from django.core.cache import cache
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
import requests

UA = "ANADICMX/1.0 (soporte@registroclustertim.com)"

TIMEOUT = (0.8, 1.8)
MX_BBOX = "-118.5,14.2,-86.4,32.9"

SESSION = requests.Session()
retry = Retry(
    total=1,
    backoff_factor=0.1,
    status_forcelist=(502, 503, 504),
    allowed_methods=frozenset(["GET"]),
)
adapter = HTTPAdapter(pool_connections=8, pool_maxsize=16, max_retries=retry)
SESSION.mount("http://", adapter)
SESSION.mount("https://", adapter)

EXEC = ThreadPoolExecutor(max_workers=8)

def _ok(data, status=200): return JsonResponse(data, status=status)
def _err(msg="no_results", code=404): return JsonResponse({"error": msg}, status=code)

def _props_from_photon(p):
    return {
        "street":      p.get("street") or p.get("name") or "",
        "housenumber": p.get("housenumber") or "",
        "district":    p.get("district") or p.get("suburb") or "",
        "city":        p.get("city") or p.get("town") or p.get("village") or "",
        "state":       p.get("state") or "",
        "postcode":    p.get("postcode") or ""
    }

def _props_from_nom(a):
    return {
        "street":      a.get("road") or a.get("pedestrian") or a.get("residential") or "",
        "housenumber": a.get("house_number") or "",
        "district":    a.get("suburb") or a.get("neighbourhood") or a.get("village") or "",
        "city":        a.get("city") or a.get("town") or a.get("municipality") or a.get("village") or "",
        "state":       a.get("state") or "",
        "postcode":    a.get("postcode") or ""
    }

def _photon_search(q, focus_lat=None, focus_lon=None):
    params = {"q": q, "lang": "es", "limit": "1", "bbox": MX_BBOX}
    if focus_lat and focus_lon:
        params["lat"] = str(focus_lat); params["lon"] = str(focus_lon)
    r = SESSION.get(
        "https://photon.komoot.io/api/",
        params=params,
        headers={"User-Agent": UA, "Accept-Language": "es"},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    data = r.json()
    f = (data.get("features") or [None])[0]
    if not f: return None
    lon, lat = f["geometry"]["coordinates"]
    props = _props_from_photon(f.get("properties") or {})
    return {"lat": float(lat), "lon": float(lon), "props": props}

def _nominatim_search(q):
    for query in (q, f"{q}, México"):
        r = SESSION.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "q": query, "format": "jsonv2", "limit": "1",
                "countrycodes": "mx", "addressdetails": "1"
            },
            headers={"User-Agent": UA, "Accept-Language": "es"},
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
        if not data: continue
        it = data[0]
        lat = float(it["lat"]); lon = float(it["lon"])
        props = _props_from_nom(it.get("address") or {})
        return {"lat": lat, "lon": lon, "props": props}
    return None

def _photon_reverse(lat, lon):
    r = SESSION.get(
        "https://photon.komoot.io/reverse",
        params={"lat": f"{lat}", "lon": f"{lon}", "lang": "es"},
        headers={"User-Agent": UA, "Accept-Language": "es"},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    data = r.json()
    f = (data.get("features") or [None])[0]
    if not f: return None
    return _props_from_photon(f.get("properties") or {})

def _nominatim_reverse(lat, lon):
    r = SESSION.get(
        "https://nominatim.openstreetmap.org/reverse",
        params={"lat": f"{lat}", "lon": f"{lon}", "format": "jsonv2", "addressdetails": "1"},
        headers={"User-Agent": UA, "Accept-Language": "es"},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    it = r.json()
    return _props_from_nom((it or {}).get("address") or {})

@require_GET
def api_geocode(request):
    q = (request.GET.get("q") or "").strip()
    if not q: return _err("missing_q", 400)

    focus_lat = request.GET.get("focus_lat")
    focus_lon = request.GET.get("focus_lon")

    key = f"geocode:{q.lower()}:{focus_lat}:{focus_lon}"
    cached = cache.get(key)
    if cached is not None:
        return _ok(cached) if "lat" in cached else _err(cached.get("error","no_results"))

    futs = [
        EXEC.submit(_photon_search, q, focus_lat, focus_lon),
        EXEC.submit(_nominatim_search, q),
    ]
    done, pending = wait(futs, timeout=2.2, return_when=FIRST_COMPLETED)
    result = None
    for f in list(done):
        try:
            result = f.result()
            if result: break
        except Exception:
            pass

    if not result:
        for f in pending:
            try:
                result = f.result(timeout=1.0)
                if result: break
            except Exception:
                pass

    for f in pending: f.cancel()

    if result:
        cache.set(key, result, 60*60)
        return _ok(result)

    cache.set(key, {"error":"no_results"}, 120)
    return _err()

@require_GET
def api_reverse(request):
    try:
        lat = float(request.GET.get("lat"))
        lon = float(request.GET.get("lon"))
    except (TypeError, ValueError):
        return _err("bad_latlon", 400)

    key = f"reverse:{lat:.6f}:{lon:.6f}"
    cached = cache.get(key)
    if cached is not None:
        return _ok(cached) if "street" in cached else _err(cached.get("error","no_results"))

    futs = [
        EXEC.submit(_photon_reverse, lat, lon),
        EXEC.submit(_nominatim_reverse, lat, lon),
    ]
    done, pending = wait(futs, timeout=2.2, return_when=FIRST_COMPLETED)
    result = None
    for f in list(done):
        try:
            result = f.result()
            if result: break
        except Exception:
            pass
    if not result:
        for f in pending:
            try:
                result = f.result(timeout=1.0)
                if result: break
            except Exception:
                pass
    for f in pending: f.cancel()

    if result:
        cache.set(key, result, 60*60)
        return _ok(result)

    cache.set(key, {"error":"no_results"}, 120)
    return _err()

@login_required
def administracion_redirect(request):
    user = request.user

    def tiene_permiso(cat):
        return bool(permisos_de_usuario(user, cat))

    if user.tipo_usuario == "super_administrador":
        return redirect('listado_eventos')

    if tiene_permiso("eventos") or tiene_permiso("archivos_evento"):
        return redirect('listado_eventos')
    if tiene_permiso("categorias_eventos"):
        return redirect('listado_categorias_eventos')
    if tiene_permiso("subcategorias_eventos"):
        return redirect('listado_subcategorias_eventos')
    if tiene_permiso("registros_eventos"):
        return redirect('listar_registros_eventos')
    if tiene_permiso("actividades"):
        return redirect('listado_actividades')
    if tiene_permiso("registros_actividades"):
        return redirect('listar_registros_actividades')
    if tiene_permiso("tipos_actividades"):
        return redirect('listado_tipos_actividades')
    if tiene_permiso("agendas"):
        return redirect('listado_agendas')
    if tiene_permiso("conferencistas"):
        return redirect('listado_expositores')
    if tiene_permiso("stands") or tiene_permiso("productos_stand") or tiene_permiso("archivos_stand"):
        return redirect('listado_stands')
    if tiene_permiso("registros_stands"):
        return redirect('listar_registros_stands')
    if tiene_permiso("horarios_citas"):
        return redirect('gestionar_horarios_citas')
    if tiene_permiso("citas"):
        return redirect('listado_citas')
    if tiene_permiso("patrocinadores"):
        return redirect('listado_patrocinadores')
    if tiene_permiso("entradas") or tiene_permiso("cupones_entrada"):
        return redirect('listado_entradas')
    if tiene_permiso("compras_entradas"):
        return redirect('listar_compras_entradas')
    if tiene_permiso("escanear_eventos"):
        return redirect('escaneo_evento')
    if tiene_permiso("escanear_actividades"):
        return redirect('escaneo_actividad')
    if tiene_permiso("escanear_stands"):
        return redirect('escaneo_stand')
    if tiene_permiso("banners"):
        return redirect('banner_principal')
    if tiene_permiso("archivos_pagina"):
        return redirect('gestionar_archivos')
    if tiene_permiso("usuarios"):
        return redirect('listar_administradores')
    if tiene_permiso("datos_pago_efectivo"):
        return redirect('configurar_pago_efectivo')

    return redirect('acceso_restringido')

@csrf_exempt
def registrar_player_id(request):
    if request.method == 'POST' and request.user.is_authenticated:
        data = json.loads(request.body.decode('utf-8'))
        player_id = data.get('player_id')

        if not player_id:
            return JsonResponse({'error': 'Falta el player_id'}, status=400)

        obj, created = OneSignalPlayer.objects.get_or_create(
            usuario=request.user,
            player_id=player_id
        )
        return JsonResponse({'status': 'ok', 'created': created})

    return JsonResponse({'error': 'No autorizado o método incorrecto'}, status=403)

@login_required
@permiso_listado('datos_pago_efectivo')
def configurar_pago_efectivo(request):
    instancia = DatosPagoEfectivoConfiguracion.objects.first()
    if not instancia:
        instancia = DatosPagoEfectivoConfiguracion()

    if request.method == 'POST':
        form = DatosPagoEfectivoForm(request.POST, instance=instancia)
        if form.is_valid():
            form.save()
            messages.success(request, "Configuración de pago en efectivo actualizada correctamente.")
            return redirect('configurar_pago_efectivo')
        else:
            messages.error(request, "Hubo errores al guardar el formulario.")
    else:
        form = DatosPagoEfectivoForm(instance=instancia)

    return render(request, 'configuraciones/pago_efectivo_configuracion.html', {'form': form})

@login_required
@permiso_listado('archivos_pagina')
def gestionar_archivos(request):
    usuario = request.user
    permisos = permisos_de_usuario(usuario, 'archivos_pagina')
    if request.method == "POST":
        form = ArchivoPaginaForm(request.POST, request.FILES)
        if form.is_valid():
            archivo = form.save(commit=False)
            archivo.save()
            messages.success(request, "Archivo subido correctamente.")
            return redirect('gestionar_archivos')
        else:
            messages.error(request, "Hubo un error al subir el archivo.")
    else:
        form = ArchivoPaginaForm()

    archivos = ArchivoPagina.objects.all()
    return render(request, "configuraciones/gestionar_archivos.html", {
        "form": form,
        "archivos": archivos,
        "permisos": permisos,
    })

@require_POST
@permiso_o_superadmin_requerido('archivos_pagina', 'editar')
def editar_archivo(request, id_archivo):
    archivo = get_object_or_404(ArchivoPagina, id=id_archivo)
    nuevo_titulo = request.POST.get("titulo")
    if nuevo_titulo:
        archivo.titulo = nuevo_titulo
        archivo.save()
        messages.success(request, "Título del archivo actualizado correctamente.")
    else:
        messages.error(request, "El título no puede estar vacío.")
    return redirect('gestionar_archivos')

@login_required
@permiso_o_superadmin_requerido('archivos_pagina', 'desactivar')
def alternar_estado_archivo(request, id):
    archivo = get_object_or_404(ArchivoPagina, id=id)
    if request.method == 'POST':
        archivo.lActivo = not archivo.lActivo
        archivo.save()
        if archivo.lActivo:
            messages.success(request, 'El archivo se activó correctamente.')
        else:
            messages.success(request, 'El archivo se desactivó correctamente.')

    return redirect('gestionar_archivos')

@require_POST
@permiso_o_superadmin_requerido('archivos_pagina', 'borrar')
def eliminar_archivo(request, id_archivo):
    archivo = get_object_or_404(ArchivoPagina, id=id_archivo)
    archivo.archivo.delete(save=False)
    archivo.delete()
    messages.success(request, "Archivo eliminado correctamente.")
    return redirect('gestionar_archivos')

@login_required
@permiso_listado('banners')
def banner_principal(request):
    usuario = request.user
    permisos = permisos_de_usuario(usuario, 'banners')
    banners = BannerPrincipal.objects.all().order_by("creado")

    if request.method == 'POST':
        form = BannerPrincipalForm(request.POST)
        if form.is_valid():
            banner = form.save(commit=False)
            base64_img = request.POST.get("imagen_base64")

            if base64_img:
                format, imgstr = base64_img.split(';base64,')
                ext = format.split('/')[-1]
                nombre = f"{uuid.uuid4().hex}.{ext}"
                banner.imagen = ContentFile(base64.b64decode(imgstr), name=nombre)

            try:
                banner.clean()
                banner.save()
                messages.success(request, "Banner agregado correctamente.")
                return redirect("banner_principal")
            except ValidationError as e:
                form.add_error(None, e.message)
        else:
            print("Errores del formulario:", form.errors)
            messages.error(request, "Error al agregar el banner.")
    else:
        form = BannerPrincipalForm()

    return render(request, "configuraciones/banners_principales.html", {
        "banners": banners,
        "form": form,
        "permisos": permisos,
    })

@login_required
@permiso_o_superadmin_requerido('banners', 'desactivar')
def alternar_estado_banner(request, id):
    banner = get_object_or_404(BannerPrincipal, id=id)
    if request.method == 'POST':
        banner.lActivo = not banner.lActivo
        banner.save()
        mensaje = 'se activó' if banner.lActivo else 'se desactivó'
        messages.success(request, f'El banner {mensaje} correctamente.')
    return redirect('banner_principal')

@login_required
@permiso_o_superadmin_requerido('banners', 'editar')
def editar_banner_principal(request, id):
    banner = get_object_or_404(BannerPrincipal, id=id)
    imagen_actual_path = banner.imagen.path if banner.imagen else None

    if request.method == 'POST':
        form = BannerPrincipalForm(request.POST, instance=banner)
        if form.is_valid():
            banner = form.save(commit=False)
            base64_img = request.POST.get("imagen_base64")

            if base64_img:
                format, imgstr = base64_img.split(';base64,')
                ext = format.split('/')[-1]
                nombre = f"{uuid.uuid4().hex}.{ext}"
                banner.imagen = ContentFile(base64.b64decode(imgstr), name=nombre)

                if imagen_actual_path and os.path.exists(imagen_actual_path):
                    os.remove(imagen_actual_path)

            banner.save()
            messages.success(request, "Banner actualizado correctamente.")
            return redirect('banner_principal')
        else:
            messages.error(request, "Error al actualizar el banner.")
    else:
        form = BannerPrincipalForm(instance=banner)

    return render(request, "configuraciones/editar_banner_principal.html", {
        'form': form,
        'banner': banner
    })

@login_required
@permiso_o_superadmin_requerido('banners', 'borrar')
def eliminar_banner_principal(request, id):
    banner = get_object_or_404(BannerPrincipal, id=id)

    if request.method == 'POST':

        imagen_path = banner.imagen.path if banner.imagen else None
        banner.delete()

        if imagen_path and os.path.exists(imagen_path):
            try:
                os.remove(imagen_path)
            except Exception as e:
                messages.warning(request, f"El banner se eliminó, pero hubo un error al eliminar la imagen: {e}")
        else:
            messages.success(request, "Banner eliminado correctamente.")
        return redirect('banner_principal')

    messages.error(request, "Solicitud inválida.")
    return redirect('banner_principal')

@csrf_exempt
@login_required
def solicitar_cita(request):
    if request.method == "POST":
        stand_id = request.POST.get("idStand")
        fecha_hora = parse_datetime(request.POST.get("fechaHora"))
        mensaje = request.POST.get("mensaje", "")

        stand = Stand.objects.get(idStand=stand_id)
        cita = CitaStand.objects.create(
            idStand=stand,
            idUsuario=request.user,
            fFechaHora=fecha_hora,
            aMensaje=mensaje,
            monto_pago=stand.nCostoCita if stand.nCostoCita > 0 else 0,
            status_pago='pendiente',
        )

        enviar_correo_cita_solicitada(cita)

        return JsonResponse({"status": "ok", "mensaje": "Cita solicitada correctamente."})
    return JsonResponse({"status": "error"}, status=400)

@login_required
def pago_cita(request, idCita):
    cita = get_object_or_404(CitaStand, idCita=idCita, idUsuario=request.user)
    if cita.aStatus != 'aceptada' or cita.status_pago == 'pagado':
        return redirect('stand', idStand=cita.idStand.idStand)

    if request.method == "POST":
        metodo = request.POST.get("metodo_pago").lower()
        cita.metodo_pago = metodo
        cita.monto_pago = cita.idStand.nCostoCita

        if metodo == "paypal":
            return redirect(reverse("paypal_payment_cita", args=[cita.idCita]))
        elif metodo == "stripe":
            return redirect(reverse("stripe_payment_cita", args=[cita.idCita]))
        elif metodo == "openpay":
            return redirect(reverse("openpay_payment_cita", args=[cita.idCita]))
        elif metodo == "presencial":
            cita.status_pago = "pendiente"
            cita.save()
            return redirect("stand", idStand=cita.idStand.idStand)

    return redirect("stand", idStand=cita.idStand.idStand)

@login_required
def pago_exitoso_cita(request, idCita, metodo_pago):
    cita = get_object_or_404(CitaStand, idCita=idCita)
    cita.status_pago = 'pagado'
    cita.metodo_pago = metodo_pago
    cita.save()

    enviar_correo_pago_cita(cita)

    return render(request, 'web/exitoso.html', {'titulo': "Pago de cita", 'tipo': "cita"})

def enviar_correo_cita_solicitada(cita):
    context = {"cita": cita}
    html_content = render_to_string("web/email_cita_solicitada.html", context)
    text_content = strip_tags(html_content)

    asunto = f"Solicitud de cita con {cita.idStand.aNombre}"
    email = EmailMultiAlternatives(asunto, text_content, "confirmacion@registroclustertim.com", [cita.idUsuario.email])
    email.attach_alternative(html_content, "text/html")
    email.send()

def enviar_correo_pago_cita(cita):
    context = {"cita": cita}
    html_content = render_to_string("web/email_pago_cita_exitoso.html", context)
    text_content = strip_tags(html_content)

    asunto = f"Confirmación de pago de cita con {cita.idStand.aNombre}"
    email = EmailMultiAlternatives(asunto, text_content, "confirmacion@registroclustertim.com", [cita.idUsuario.email])
    email.attach_alternative(html_content, "text/html")
    email.send()

def paypal_payment_cita(request, idCita):
    cita = get_object_or_404(CitaStand, idCita=idCita)

    paypal_params = {
        "cmd": "_xclick",
        "business": settings.PAYPAL_RECEIVER_EMAIL,
        "amount": cita.monto_pago,
        "currency_code": "MXN",
        "item_name": f"Cita con {cita.idStand.aNombre}",
        "invoice": f"CITA-{cita.idCita}-{request.user.idUsuario}",
        "notify_url": request.build_absolute_uri(reverse("paypal-ipn")),
        "return": request.build_absolute_uri(reverse("pago_exitoso_cita", args=[cita.idCita, "paypal"])),
        "cancel_return": request.build_absolute_uri(reverse("pago_cancelado")),
    }

    url = "https://www.sandbox.paypal.com/cgi-bin/webscr?" + urllib.parse.urlencode(paypal_params)
    return redirect(url)

def stripe_payment_cita(request, idCita):
    cita = get_object_or_404(CitaStand, idCita=idCita)

    stripe.api_key = settings.STRIPE_SECRET_KEY

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "mxn",
                "product_data": {
                    "name": f"Cita con {cita.idStand.aNombre}",
                },
                "unit_amount": int(cita.monto_pago * 100),
            },
            "quantity": 1,
        }],
        mode="payment",
        success_url=request.build_absolute_uri(reverse("pago_exitoso_cita", args=[cita.idCita, "stripe"])),
        cancel_url=request.build_absolute_uri(reverse("pago_cancelado")),
    )

    return redirect(session.url)

def openpay_payment_cita(request, idCita):
    cita = get_object_or_404(CitaStand, idCita=idCita)

    OPENPAY_URL = f"https://sandbox-api.openpay.mx/v1/{settings.OPENPAY_MERCHANT_ID}/charges"

    headers = {
        "Authorization": "Basic " + base64.b64encode(f"{settings.OPENPAY_PRIVATE_KEY}:".encode()).decode(),
        "Content-Type": "application/json"
    }

    payload = {
        "method": "card",
        "source_id": "tok_test_visa",
        "amount": float(cita.monto_pago),
        "currency": "MXN",
        "description": f"Pago de cita con {cita.idStand.aNombre}",
        "order_id": f"CITA-{cita.idCita}-{request.user.idUsuario}",
        "device_session_id": request.session.session_key,
        "customer": {
            "name": request.user.aNombre,
            "last_name": request.user.aApellido,
            "email": request.user.email,
        }
    }

    response = requests.post(OPENPAY_URL, json=payload, headers=headers)

    if response.status_code == 200:
        return redirect(reverse("pago_exitoso_cita", args=[cita.idCita, "openpay"]))
    else:
        return redirect(reverse("pago_cancelado"))

def login_view(request):
    if request.user.is_authenticated:
        return redirect('index' if request.user.tipo_usuario == 'cliente' else 'administracion_redirect')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        remember_me = request.POST.get('remember_me')

        user = authenticate(request, username=username, password=password)

        if user is not None and user.lActivo:
            if not user.verificado:
                messages.error(request, "Debes verificar tu correo antes de iniciar sesión.")
                return redirect('verificacion_pendiente')

            login(request, user)

            next_url = request.GET.get('next')
            if not next_url:
                next_url = 'index'

            response = redirect(next_url)

            if remember_me:
                response.set_cookie('remember_username', username, max_age=1209600)
                response.set_cookie('remember_password', password, max_age=1209600)
            else:
                response.delete_cookie('remember_username')
                response.delete_cookie('remember_password')

            return response
        else:
            messages.error(request, 'Credenciales inválidas o usuario inactivo')

    username = request.COOKIES.get('remember_username', '')
    password = request.COOKIES.get('remember_password', '')

    next_url = request.GET.get('next', '')

    return render(request, 'web/login.html', {
        'remember_username': username,
        'remember_password': password,
        'next_url': next_url
    })

def registro_no_socio(request):
    if request.user.is_authenticated:
        return redirect('index')

    if request.method == 'POST':
        form = RegistroNoSocioForm(request.POST)
        if form.is_valid():
            usuario = form.save(commit=False)
            usuario.tipo_usuario = 'cliente'
            usuario.set_password(form.cleaned_data['password'])
            usuario.verificado = False
            usuario.save()
            enviar_correo_verificacion(usuario)
            messages.success(request, "Registro exitoso. Revisa tu correo para activar tu cuenta.")
            return redirect('verificacion_pendiente')
    else:
        form = RegistroNoSocioForm()

    return render(request, 'web/registro.html', {'form': form})

def enviar_correo_verificacion(usuario):
    token = usuario.token_verificacion
    link_verificacion = f"https://registroclustertim.com{reverse('verificar_email', args=[token])}"

    context = {'usuario': usuario, 'link_verificacion': link_verificacion}
    html_content = render_to_string('web/email_verificacion.html', context)
    text_content = strip_tags(html_content)

    asunto = "Verifica tu cuenta en EVENTOS CLUSTERTIM"
    email = EmailMultiAlternatives(asunto, text_content, 'verificacion@registroclustertim.com', [usuario.email])
    email.attach_alternative(html_content, "text/html")
    email.send()

def reenviar_verificacion(request):
    if request.method == 'POST':
        form = ReenviarVerificacionForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            usuario = Usuario.objects.filter(email=email, verificado=False).first()

            if usuario:
                enviar_correo_verificacion(usuario)
                messages.success(request, "Correo de verificación reenviado. Revisa tu bandeja de entrada.")
            else:
                messages.error(request, "El correo ingresado no está registrado o ya ha sido verificado.")

            return redirect('verificacion_pendiente')
    else:
        form = ReenviarVerificacionForm()

    return render(request, 'web/reenviar_verificacion.html', {'form': form})

def verificar_email(request, token):
    usuario = get_object_or_404(Usuario, token_verificacion=token)

    if usuario.verificado:
        messages.success(request, "Tu cuenta ya está verificada.")
    else:
        usuario.verificado = True
        usuario.save()
        messages.success(request, "Correo verificado con éxito. Ahora puedes iniciar sesión.")

    return redirect('login')

def acceso_restringido(request):
    return render(request, 'web/acceso_restringido.html')

@login_required
def perfil_view(request):
    usuario = request.user

    if not usuario.aQr:
        usuario.aQr = generar_qr_string(usuario)
        usuario.save()

    if request.method == 'POST':
        form = PerfilForm(request.POST, request.FILES, instance=usuario)
        foto_base64 = request.POST.get('foto_recortada')

        if form.is_valid():
            usuario = form.save(commit=False)

            if foto_base64:

                header, imgstr = foto_base64.split(';base64,')
                ext = 'png'

                if usuario.foto_perfil:
                    try:
                        usuario.foto_perfil.delete(save=False)
                    except Exception:
                        pass

                random_name = f"perfil_{uuid.uuid4().hex}.{ext}"
                usuario.foto_perfil.save(
                    random_name,
                    ContentFile(base64.b64decode(imgstr)),
                    save=False
                )

            usuario.save()
            messages.success(request, "Perfil actualizado con éxito.")
            return redirect('perfil')
    else:
        form = PerfilForm(instance=usuario, initial={
            'usar_mismo_numero': usuario.aWhatsapp == usuario.aTelefono
        })

    qr_data = str(usuario.idUsuario) + "+" + str(usuario.aQr)
    qr = qrcode.make(qr_data)
    buffer = BytesIO()
    qr.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()

    return render(request, 'web/perfil.html', {
        'form': form,
        'usuario': usuario,
        'qr_base64': qr_base64,
    })

def recortar_imagen_circular(imagen_path):
    img = Image.open(imagen_path).convert("RGBA")
    size = min(img.size)
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size, size), fill=255)
    img = img.crop(((img.width - size) // 2, (img.height - size) // 2, (img.width + size) // 2, (img.height + size) // 2))
    img.putalpha(mask)
    output = BytesIO()
    img.save(output, format="PNG")
    output.seek(0)
    return output

def generar_gafete_pdf(usuario):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=portrait((250, 400)))

    p.setFillColorRGB(0.2, 0.2, 0.6)
    p.rect(0, 0, 250, 400, fill=1)
    p.setFillColorRGB(1, 1, 1)
    p.rect(10, 50, 230, 340, fill=1, stroke=0)

    if usuario.foto_perfil:
        img_circular = recortar_imagen_circular(usuario.foto_perfil.path)
        img_reader = ImageReader(img_circular)
        p.drawImage(img_reader, 75, 280, 100, 100, mask='auto')

    p.setFillColorRGB(0, 0, 0)
    p.setFont("Helvetica-Bold", 12)
    nombre_completo = f"{usuario.aNombre} {usuario.aApellido}"
    p.drawCentredString(125, 260, nombre_completo)

    p.setFont("Helvetica", 10)
    p.drawCentredString(125, 245, usuario.email)

    if usuario.aEmpresa:
        p.setFont("Helvetica-Bold", 10)
        p.drawCentredString(125, 225, "Empresa:")
        p.setFont("Helvetica", 10)
        p.drawCentredString(125, 210, usuario.aEmpresa)

    qr_data = str(usuario.idUsuario) + "+" + usuario.aQr
    qr_image = qrcode.make(qr_data)
    qr_buffer = BytesIO()
    qr_image.save(qr_buffer, format="PNG")
    qr_reader = ImageReader(qr_buffer)
    p.drawImage(qr_reader, 75, 50, 100, 100, preserveAspectRatio=True, mask='auto')

    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

@login_required
def descargar_gafete(request):
    usuario = request.user
    pdf_buffer = generar_gafete_pdf(usuario)
    response = HttpResponse(pdf_buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Gafete_{usuario.aNombre}.pdf"'
    return response

@login_required
def instrucciones_pago_efectivo(request, compra_id, formato='html'):

    compra = get_object_or_404(
        CompraEntrada,
        idCompra=compra_id,
        usuario=request.user,
        metodo_pago='efectivo',
        status_pago='pendiente',
    )

    datos = DatosPagoEfectivoConfiguracion.objects.filter(lActivo=True).first()
    if not datos:
        raise Http404("Aún no hay configuración activa para pagos en efectivo.")

    context = {
        "compra": compra,
        "datos_pago": datos,

        "render_origen": "mis_compras",
    }

    if formato == 'pdf':

        from weasyprint import HTML

        html = render_to_string("web/email_pago_efectivo.html", context)

        base_url = request.build_absolute_uri('/')
        pdf_bytes = HTML(string=html, base_url=base_url).write_pdf()

        filename = f"instrucciones_pago_{compra.idCompra}.pdf"
        response = HttpResponse(pdf_bytes, content_type="application/pdf")

        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response

    return render(request, "web/email_pago_efectivo.html", context)

@login_required
def mis_compras(request):
    usuario = request.user

    if request.method == "POST":

        if 'comprobante_pago' in request.FILES:
            compra_id = request.POST.get("compra_id")
            compra = get_object_or_404(CompraEntrada, idCompra=compra_id, usuario=usuario, metodo_pago='efectivo', status_pago='pendiente')

            compra.comprobante_pago = request.FILES['comprobante_pago']
            compra.save()
            messages.success(request, "Tu comprobante fue subido correctamente. Un administrador revisará tu pago.")
            return redirect("mis_compras")

        codigo_ingresado = request.POST.get("codigo", "").strip()
        try:
            codigo = CodigoEntrada.objects.get(codigo=codigo_ingresado, activado_por__isnull=True)
            codigo.activado_por = usuario
            codigo.fecha_activacion = ahora_mx()
            codigo.save()

            compra = codigo.compra
            entrada = compra.entrada

            if not RegistroEvento.objects.filter(usuario=usuario, evento=entrada.idEvento).exists():
                RegistroEvento.objects.create(usuario=usuario, evento=entrada.idEvento)

            for entrada_actividad in entrada.actividades_incluidas.all():
                actividad = entrada_actividad.idActividad
                if not RegistroActividad.objects.filter(usuario=usuario, actividad=actividad).exists():
                    RegistroActividad.objects.create(usuario=usuario, actividad=actividad)

            messages.success(request, "El código ha sido canjeado exitosamente. La entrada ya está activada en tu cuenta.")
            return redirect("mis_compras")
        except CodigoEntrada.DoesNotExist:
            messages.error(request, "El código no es válido o ya ha sido usado.")

    compras_directas = CompraEntrada.objects.filter(
        Q(usuario=usuario, status_pago="pagado") |
        Q(usuario=usuario, status_pago="pendiente", metodo_pago="efectivo")
    )

    codigos_canjeados = CodigoEntrada.objects.filter(activado_por=usuario).select_related("compra")

    return render(request, "web/mis_compras.html", {
        "compras_directas": compras_directas,
        "codigos_canjeados": codigos_canjeados,
    })

def privacidad(request):
    return render(request, 'web/privacidad.html')

def index(request):
    request.session.pop("navbar_logo_url", None)
    banners = BannerPrincipal.objects.all().order_by('creado')

    hoy = ahora_mx().date()
    eventos = Evento.objects.filter(fFechaFin__date__gte=hoy)

    return render(request, 'web/index.html', {
        'banners': banners,
        'eventos': eventos,
    })

def evento_detalles(request, idEvento):
    request.session['ultimo_evento_id'] = idEvento
    evento = get_object_or_404(Evento, idEvento=idEvento)

    patrocinadores = Patrocinador.objects.filter(idEvento=idEvento)
    fecha_inicio = evento.fFechaInicio
    fecha_fin = evento.fFechaFin

    categoria = getattr(evento, "categoria", None) or getattr(evento, "idCategoria", None)
    estilo = getattr(categoria, "estilo_detalle_evento", "1") if categoria else "1"
    template_name = 'web/detalles_evento.html' if str(estilo) == '1' else 'web/detalles_evento2.html'

    dia_inicio = fecha_inicio.day
    mes_inicio = fecha_inicio.strftime('%b')
    año_inicio = fecha_inicio.year

    dia_fin = fecha_fin.day
    mes_fin = fecha_fin.strftime('%b')
    año_fin = fecha_fin.year

    if año_inicio == año_fin:
        if mes_inicio == mes_fin:
            fecha_formateada = f"{dia_inicio}-{dia_fin} {mes_inicio}, {año_inicio}"
        else:
            fecha_formateada = f"{dia_inicio} {mes_inicio}-{dia_fin} {mes_fin}, {año_inicio}"
    else:
        fecha_formateada = f"{dia_inicio} {mes_inicio} {año_inicio}-{dia_fin} {mes_fin} {año_fin}"

    dia_inicio_counter = fecha_inicio.day

    meses_espanol = [
        'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
        'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
    ]

    mes_año_inicio = f"{meses_espanol[fecha_inicio.month - 1]} {fecha_inicio.year}"

    data = []
    actividades_registradas = []

    if request.user.is_authenticated:
        actividades_registradas = RegistroActividad.objects.filter(usuario=request.user).values_list('actividad_id', flat=True)

    agendas = Agenda.objects.filter(idEvento=evento, lVisible=True, lActivo=True)

    for agenda in agendas:
        actividades_agenda = AgendaActividades.objects.filter(idAgenda=agenda).select_related('idActividad')

        actividades_por_dia = {}
        for ag_act in actividades_agenda:
            actividad = ag_act.idActividad
            fecha_str = actividad.fFechaHoraInicio.strftime("%Y-%m-%d")

            expositores = ExpositorActividad.objects.filter(idActividad=actividad).select_related('idExpositor')
            expositores_nombres = ", ".join([exp.idExpositor.aNombre for exp in expositores]) if expositores.exists() else "Sin expositor"

            if actividad.idActividad in actividades_registradas:
                if actividad.lAcompañantes:
                    boton = "Editar acompañantes"
                else:
                    boton = None
            else:
                if actividad.nCosto > 0:
                    boton = "Comprar pase"
                elif actividad.nCosto == 0 and actividad.lAcompañantes:
                    boton = "Registrarse"
                else:
                    boton = None

            actividad_data = {
                "id": actividad.idActividad,
                "hora": f"{actividad.fFechaHoraInicio.strftime('%I:%M%p')} - {actividad.fFechaHoraFin.strftime('%I:%M%p')}",
                "nombre": actividad.aNombre,
                "expositor": expositores_nombres,
                "lugar": actividad.dDireccion if actividad.dDireccion else "Lugar del evento",
                "latitud": "{:.6f}".format(actividad.dLatitud) if actividad.dLatitud else None,
                "longitud": "{:.6f}".format(actividad.dLongitud) if actividad.dLongitud else None,
                "fecha_hora_inicio": actividad.fFechaHoraInicio,
                "boton": boton,
            }

            if fecha_str not in actividades_por_dia:
                actividades_por_dia[fecha_str] = []
            actividades_por_dia[fecha_str].append(actividad_data)

        dias_ordenados = sorted(actividades_por_dia.items(), key=lambda x: datetime.strptime(x[0], "%Y-%m-%d"))
        for fecha, actividades in dias_ordenados:
            actividades.sort(key=lambda x: x["fecha_hora_inicio"])

        data.append({
            "agenda": agenda.aNombre,
            "dias": dict(dias_ordenados)
        })

    actividades = Actividad.objects.filter(idEvento=idEvento)
    expositores = Expositor.objects.filter(actividades__idActividad__in=actividades).distinct()

    entradas = list(Entrada.objects.filter(idEvento=evento, lActivo=True))

    actividad_principal = Actividad(aNombre="Entrada al evento", nCapacidad=1000000,
                                    nLugaresDisponibles=1000000, fFechaHoraInicio=evento.fFechaInicio,
                                    fFechaHoraFin=evento.fFechaFin, idEvento_id=evento.idEvento)

    entradas_a_imprimir = []

    if evento.lGratuito:
        entrada_gratuita = {
            'aNombre': 'Entrada gratuita',
            'nCosto': 0,
            'actividades': [actividad_principal],
            'disponible': True
        }
        entradas_a_imprimir.append(entrada_gratuita)

    for entrada in entradas:
        actividades_entrada = list(Actividad.objects.filter(entradas_incluidas__idEntrada=entrada))
        actividades_entrada.insert(0, actividad_principal)
        disponible = entrada.nCantidad > 0
        entrada_a_imprimir = {
            'idEntrada': entrada.idEntrada,
            'aNombre': entrada.aNombre,
            'nCosto': entrada.nCosto,
            'actividades': actividades_entrada,
            'nCantidad': entrada.nCantidad,
            'disponible': disponible
        }
        entradas_a_imprimir.append(entrada_a_imprimir)

    entradas_compradas = []
    if request.user.is_authenticated:
        entradas_compradas = list(
            CompraEntrada.objects.filter(
                usuario=request.user,
                status_pago='pagado'
            ).values_list('entrada_id', flat=True)
        )

    return render(request, template_name, {
        'evento': evento,
        'expositores': expositores,
        'patrocinadores': patrocinadores,
        "agendas": data,
        'entradas': entradas_a_imprimir,
        'fecha_formateada': fecha_formateada,
        'dia_inicio_counter': dia_inicio_counter,
        'mes_año_inicio': mes_año_inicio,
        'entradas_compradas': entradas_compradas,
    })

def _ensure_aware(dt):

    if dt is None:
        return None
    if timezone.is_naive(dt):
        return timezone.make_aware(dt, timezone.get_default_timezone())
    return dt

def _to_local_str(dt, fmt):

    if dt is None:
        return ""
    aware = _ensure_aware(dt)
    dt_local = aware.astimezone(timezone.get_current_timezone())
    return dt_local.strftime(fmt)

def actividad_detalles_api(request, idActividad):
    actividad = get_object_or_404(
        Actividad.objects.select_related('idEvento', 'idTipo'),
        pk=idActividad
    )
    evento = actividad.idEvento

    if not getattr(evento, 'lAgendaVisible', True) and not request.user.is_authenticated:
        return JsonResponse({'error': 'Agenda no disponible'}, status=403)

    exps_qs = (
        ExpositorActividad.objects
        .filter(idActividad=actividad)
        .select_related('idExpositor')
    )
    expositores = []
    for ea in exps_qs:
        e = ea.idExpositor
        expositores.append({
            'id': getattr(e, 'idExpositor', None),
            'nombre': f"{getattr(e, 'aNombre', '')} {getattr(e, 'aApellido', '')}".strip() or "Sin nombre",
            'foto': (e.aFoto.url if getattr(e, 'aFoto', None) else None),
            'facebook': getattr(e, 'aFacebook', None) or None,
            'twitter': getattr(e, 'aTwitter', None) or None,
            'instagram': getattr(e, 'aInstagram', None) or None,
            'web': getattr(e, 'aSitioWeb', None) or None,
            'email': getattr(e, 'aEmail', None) or None,
            'perfil_url': reverse('expositor_detalles', args=[e.idExpositor]) if getattr(e, 'idExpositor', None) else None,
        })

    fecha = _to_local_str(actividad.fFechaHoraInicio, '%d/%m/%Y')
    hora_inicio = _to_local_str(actividad.fFechaHoraInicio, '%H:%M')
    hora_fin    = _to_local_str(actividad.fFechaHoraFin, '%H:%M')
    hora = f"{hora_inicio} - {hora_fin}" if hora_inicio and hora_fin else ""

    if actividad.lMismaDireccion or not (actividad.dCalle or actividad.dDireccion):
        direccion = " ".join(filter(None, [
            getattr(evento, 'dCalle', ''),
            getattr(evento, 'dNumero', ''),
            getattr(evento, 'dColonia', ''),
            getattr(evento, 'dCP', ''),
            getattr(evento, 'dCiudad', ''),
            getattr(evento, 'dEstado', ''),
        ])).strip()
        lat = getattr(evento, 'dLatitud', None)
        lng = getattr(evento, 'dLongitud', None)
    else:
        direccion = (actividad.dDireccion or " ".join(filter(None, [
            actividad.dCalle, actividad.dNumero, actividad.dColonia,
            actividad.dCP, actividad.dCiudad, actividad.dEstado
        ]))).strip()
        lat = actividad.dLatitud
        lng = actividad.dLongitud

    lat = float(lat) if lat is not None else None
    lng = float(lng) if lng is not None else None
    maps_url = f"https://www.google.com/maps/dir/?api=1&destination={lat},{lng}" if (lat is not None and lng is not None) else None

    ahora_aware = _ensure_aware(timezone.now())
    fin_evento_aware = _ensure_aware(evento.fFechaFin)
    evento_terminado = (fin_evento_aware < ahora_aware) if fin_evento_aware else False

    cta, cta_url = None, None
    if not evento_terminado:
        registrado = False
        if request.user.is_authenticated:
            registrado = RegistroActividad.objects.filter(
                usuario=request.user,
                actividad_id=actividad.idActividad
            ).exists()

        if registrado:
            if actividad.lAcompañantes:
                cta = "Editar acompañantes"
                cta_url = reverse('editar_acompañantes', args=[actividad.idActividad])
            else:
                cta = "Ya registrado"
        else:
            costo_float = float(actividad.nCosto or 0)
            if costo_float > 0:
                cta = "Comprar pase"
                cta_url = reverse('pago_actividad', args=[actividad.idActividad])
            else:
                if actividad.lAcompañantes:
                    cta = "Registrarse"
                    cta_url = reverse('registro_acompañantes_actividad', args=[actividad.idActividad])
                else:
                    cta = "Registro gratuito"
                    cta_url = reverse('registro_gratuito_simple', args=[actividad.idActividad])

    data = {
        'id': actividad.idActividad,
        'nombre': actividad.aNombre,
        'descripcion': actividad.aDescripcion or "",
        'tipo': actividad.idTipo.aNombre if actividad.idTipo else None,
        'costo': f"{float(actividad.nCosto or 0):.2f}",
        'capacidad': actividad.nCapacidad,
        'disponibles': actividad.nLugaresDisponibles,
        'fecha': fecha,
        'hora': hora,
        'lugar': direccion or "Lugar del evento",
        'maps_url': maps_url,
        'expositores': expositores,
        'permite_acompanantes': actividad.lAcompañantes,
        'max_acompanantes': actividad.nAcompañantes,
        'cta': cta,
        'cta_url': cta_url,
        'evento_terminado': evento_terminado,
    }
    return JsonResponse(data)

DEFAULT_BASE_URL = getattr(settings, "SITE_URL", "https://eventos.anadicmexico.mx")
DEFAULT_FROM = getattr(settings, "DEFAULT_FROM_EMAIL", "notificaciones@eventos.anadicmexico.mx")

def _abs_url(path: str) -> str:
    base = DEFAULT_BASE_URL.rstrip("/")
    return f"{base}{path}"

def expositor_detalles(request, idExpositor):
    idExpositor = idExpositor
    detalles = get_object_or_404(Expositor, idExpositor=idExpositor)
    archivos_expositor = []
    archivos_queryset = ArchivoExpositor.objects.filter(expositor=expositor)
    for archivo in archivos_queryset:
        ext = os.path.splitext(archivo.archivo.name)[1]
        archivo.extension = ext[1:].upper() if ext else ''
        archivos_expositor.append(archivo)

    return render(request, 'web/detalles.html', {'detalles': detalles, 'tipo':"conferencista",
        "archivos_expositor": archivos_expositor,})

def patrocinador_detalles(request, idPatrocinador):
    idPatrocinador = idPatrocinador
    detalles = get_object_or_404(Patrocinador, idPatrocinador=idPatrocinador)

    return render(request, 'web/detalles_patro.html', {'detalles': detalles, 'tipo':"patrocinador"})

def stands(request, idEvento):
    stands = Stand.objects.filter(idEvento=idEvento)

    return render(request, 'web/stands.html', {'stands': stands})

def stand(request, idStand):
    stand = get_object_or_404(Stand, idStand=idStand)
    patrocinador = Patrocinador.objects.filter(idStand=idStand).first()
    productos_list = stand.productos.all()
    paginator = Paginator(productos_list, 12)
    page_number = request.GET.get('page')
    productos = paginator.get_page(page_number)

    cita_activa = None
    pago_pendiente = False

    if request.user.is_authenticated:
        cita_activa = CitaStand.objects.filter(
            idStand=stand,
            idUsuario=request.user,
            aStatus__in=["pendiente", "aceptada"]
        ).first()
        if cita_activa and cita_activa.status_pago != 'pagado':
            pago_pendiente = True

    citas_aceptadas = CitaStand.objects.filter(
        idStand=stand,
        aStatus='aceptada'
    ).values_list('fFechaHora', flat=True)

    horas_ocupadas = set(dt.strftime('%Y-%m-%d %H:%M') for dt in citas_aceptadas)

    horarios_disponibles = [
        h for h in HorarioCita.objects.filter(idStand=stand, fFechaHora__gte=ahora_mx()).order_by('fFechaHora')
        if h.fFechaHora.strftime('%Y-%m-%d %H:%M') not in horas_ocupadas
    ]

    archivos_stand = []
    archivos_queryset = ArchivoStand.objects.filter(stand=stand)
    for archivo in archivos_queryset:
        ext = os.path.splitext(archivo.archivo.name)[1]
        archivo.extension = ext[1:].upper() if ext else ''
        archivos_stand.append(archivo)

    context = {
        'stand': stand,
        'patrocinador': patrocinador,
        'productos': productos,
        "cita_activa": cita_activa,
        "pago_pendiente": pago_pendiente,
        "horarios_disponibles": horarios_disponibles,
        "archivos_stand": archivos_stand,
    }

    return render(request, 'web/stand.html', context)

def calcular_monto_final(entrada, cantidad, cupon_aplicado):
    monto_unitario = entrada.nCosto

    if cupon_aplicado:
        if cupon_aplicado.eTipo == 'porcentaje':
            descuento = monto_unitario * (cupon_aplicado.nValor / 100)
        else:
            descuento = min(cupon_aplicado.nValor, monto_unitario)

        if cupon_aplicado.lAplicaTotal:
            return max((monto_unitario * cantidad) - (descuento * cantidad), 0)
        else:
            return max((monto_unitario * (cantidad - 1)) + (monto_unitario - descuento), 0)
    else:
        return monto_unitario * cantidad

@login_required
def pago_entrada(request, idEntrada):
    entrada = get_object_or_404(Entrada, idEntrada=idEntrada)
    cantidad = 1
    cupon_aplicado = None
    compra = None
    monto_final = entrada.nCosto

    if entrada.nCantidad <= 0:
        messages.error(request, "Ya no hay disponibilidad para esta entrada.")
        return redirect("evento_detalles", idEvento=entrada.idEvento.idEvento)

    if request.method == "POST":
        cantidad = int(request.POST.get("cantidad", "1"))
        if not entrada.lMultiple:
            cantidad = 1
        if cantidad <= 0 or cantidad > entrada.nCantidad:
            messages.error(request, "La cantidad solicitada no está disponible.")
            return redirect("pago_entrada", idEntrada=entrada.idEntrada)

        cupon_codigo = request.POST.get("cupon", "").strip()
        metodo_pago = request.POST.get("metodo_pago", "").strip().lower()

        if cupon_codigo:
            try:
                cupon = Cupon.objects.get(aCodigo=cupon_codigo.upper(), entrada=entrada, lActivo=True)
                if cupon.nLimiteUso is None or cupon.nUsados < cupon.nLimiteUso:
                    cupon_aplicado = cupon
                else:
                    messages.error(request, "El cupón ya fue canjeado por completo.")
                    return redirect("pago_entrada", idEntrada=entrada.idEntrada)
            except Cupon.DoesNotExist:
                messages.error(request, "El cupón no es válido para esta entrada.")
                return redirect("pago_entrada", idEntrada=entrada.idEntrada)

        monto_final = calcular_monto_final(entrada, cantidad, cupon_aplicado)
        print(f"[DEBUG] Cantidad: {cantidad}, Monto final calculado: {monto_final}")

        if metodo_pago:
            if metodo_pago == "gratuito" and monto_final == 0:
                compra = CompraEntrada.objects.create(
                    usuario=request.user,
                    entrada=entrada,
                    metodo_pago="gratuito_cuponado",
                    monto_pago=0,
                    status_pago="pendiente",
                    cupon=cupon_aplicado,
                    nCantidad=cantidad
                )
                return redirect("registro_por_cupon", idEntrada=entrada.idEntrada, compra_id=compra.idCompra)

            elif metodo_pago == "efectivo":
                compra = CompraEntrada.objects.create(
                    usuario=request.user,
                    entrada=entrada,
                    metodo_pago="efectivo",
                    monto_pago=monto_final,
                    status_pago="pendiente",
                    cupon=cupon_aplicado,
                    nCantidad=cantidad
                )
                enviar_correo_pago_efectivo(compra)
                return redirect("pago_pendiente", compra_id=compra.idCompra)

            compra = CompraEntrada.objects.create(
                usuario=request.user,
                entrada=entrada,
                metodo_pago=metodo_pago,
                monto_pago=monto_final,
                status_pago="pendiente",
                cupon=cupon_aplicado,
                nCantidad=cantidad
            )
            return redirect(reverse(f"{metodo_pago}_payment", args=[entrada.idEntrada, compra.idCompra]))

    else:

        monto_final = calcular_monto_final(entrada, cantidad, None)

    metodos_pago = []
    if monto_final >= 10:
        metodos_pago.append("Stripe")
    metodos_pago.append("PayPal")
    if DatosPagoEfectivoConfiguracion.objects.filter(lActivo=True).exists():
        metodos_pago.append("Efectivo")

    return render(request, "web/pago_entrada.html", {
        "entrada": entrada,
        "monto_final": monto_final,
        "cupon_aplicado": cupon_aplicado,
        "metodos_pago": metodos_pago,
        "compra": compra if monto_final == 0 else None,
        "cantidad": cantidad,
    })

def enviar_correo_pago_efectivo(compra):
    datos = DatosPagoEfectivoConfiguracion.objects.filter(lActivo=True).first()
    if not datos:
        return

    context = {
        "compra": compra,
        "datos_pago": datos
    }
    html_content = render_to_string("web/email_pago_efectivo.html", context)
    text_content = strip_tags(html_content)

    asunto = f"Pago pendiente: {compra.entrada.aNombre}"
    email = EmailMultiAlternatives(asunto, text_content, "confirmacion@registroclustertim.com", [compra.usuario.email])
    email.attach_alternative(html_content, "text/html")
    email.send()

def enviar_correo_confirmacion(compra):
    context = {"compra": compra}
    html_content = render_to_string("web/email_confirmacion.html", context)
    text_content = strip_tags(html_content)

    asunto = f"Confirmación de compra: {compra.entrada.aNombre}"
    email = EmailMultiAlternatives(asunto, text_content, "confirmacion@registroclustertim.com", [compra.usuario.email])
    email.attach_alternative(html_content, "text/html")
    email.send()

def paypal_payment(request, idEntrada, compra_id):
    compra = get_object_or_404(CompraEntrada, idCompra=compra_id, entrada__idEntrada=idEntrada)
    entrada = compra.entrada

    paypal_params = {
        "cmd": "_xclick",
        "business": settings.PAYPAL_RECEIVER_EMAIL,
        "amount": f"{compra.monto_pago:.2f}",
        "currency_code": "MXN",
        "item_name": f"{entrada.aNombre} x {compra.nCantidad}",
        "invoice": f"INV-{entrada.idEntrada}-{request.user.idUsuario}",
        "notify_url": request.build_absolute_uri(reverse("paypal-ipn")),
        "return": request.build_absolute_uri(reverse("pago_exitoso", args=[entrada.idEntrada, "paypal", compra.idCompra])),
        "cancel_return": request.build_absolute_uri(reverse("pago_cancelado")),
    }

    paypal_url = "https://www.paypal.com/cgi-bin/webscr?" + urllib.parse.urlencode(paypal_params)
    return redirect(paypal_url)

def stripe_payment(request, idEntrada, compra_id):
    compra = get_object_or_404(CompraEntrada, idCompra=compra_id, entrada__idEntrada=idEntrada)
    stripe.api_key = settings.STRIPE_SECRET_KEY

    monto_final = float(compra.monto_pago)

    if monto_final < 10:
        messages.error(request, "Stripe no permite pagos menores a $10.00 MXN.")
        return redirect("pago_entrada", idEntrada=idEntrada)

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "mxn",
                "product_data": {
                    "name": f"{compra.entrada.aNombre} x {compra.nCantidad}",
                },
                "unit_amount": int(compra.monto_pago * 100),
            },
            "quantity": 1,
        }],
        mode="payment",
        success_url=request.build_absolute_uri(reverse("pago_exitoso", args=[compra.entrada.idEntrada, "stripe", compra.idCompra])),
        cancel_url=request.build_absolute_uri(reverse("pago_cancelado")),
    )

    return redirect(session.url)

def openpay_payment(request, idEntrada, compra_id):
    compra = get_object_or_404(CompraEntrada, idCompra=compra_id, entrada__idEntrada=idEntrada)
    entrada = compra.entrada

    OPENPAY_URL = f"https://sandbox-api.openpay.mx/v1/{settings.OPENPAY_MERCHANT_ID}/charges"

    headers = {
        "Authorization": "Basic " + base64.b64encode(f"{settings.OPENPAY_PRIVATE_KEY}:".encode()).decode(),
        "Content-Type": "application/json"
    }

    payload = {
        "method": "card",
        "source_id": "tok_test_visa",
        "amount": float(compra.monto_pago),
        "currency": "MXN",
        "description": f"Pago por entrada: {entrada.aNombre}",
        "order_id": f"ORD-{entrada.idEntrada}-{request.user.idUsuario}",
        "device_session_id": request.session.session_key,
        "customer": {
            "name": request.user.first_name,
            "last_name": request.user.last_name,
            "email": request.user.email,
        }
    }

    response = requests.post(OPENPAY_URL, json=payload, headers=headers)

    if response.status_code == 200:
        return redirect(reverse("pago_exitoso", args=[entrada.idEntrada, "openpay", compra.idCompra]))
    else:
        return redirect(reverse("pago_cancelado"))

@login_required
def pago_pendiente(request, compra_id):
    compra = get_object_or_404(CompraEntrada, idCompra=compra_id, usuario=request.user)

    if compra.metodo_pago != "efectivo":
        return redirect("index")

    entrada = compra.entrada

    if compra.status_pago == "pendiente":
        if not entrada.lMultiple:
            if entrada.nCantidad >= 1:
                entrada.nCantidad -= 1
                entrada.save()

                for entrada_actividad in entrada.actividades_incluidas.all():
                    actividad = entrada_actividad.idActividad
                    if actividad.nLugaresDisponibles >= 1:
                        actividad.nLugaresDisponibles -= 1
                        actividad.save()
        else:
            if entrada.nCantidad >= compra.nCantidad:
                entrada.nCantidad -= compra.nCantidad
                entrada.save()

        if compra.cupon and compra.cupon.nUsados < compra.cupon.nLimiteUsos:
            compra.cupon.nUsados += 1
            compra.cupon.save()

    return render(request, "web/pago_pendiente.html", {
        "compra": compra,
        "titulo": "Compra",
        "tipo": "registro"
    })

@login_required
def pago_exitoso(request, idEntrada, metodo_pago, compra_id):
    compra = get_object_or_404(CompraEntrada, idCompra=compra_id, entrada__idEntrada=idEntrada)

    if compra.status_pago != "pagado":
        compra.status_pago = "pagado"
        compra.save()

        entrada = compra.entrada

        if not entrada.lMultiple:
            entrada.nCantidad -= 1
            entrada.nVendidas += 1
            entrada.save()

            if compra.cupon:
                compra.cupon.nUsados += 1
                compra.cupon.save()

            if not RegistroEvento.objects.filter(usuario=request.user, evento=entrada.idEvento).exists():
                RegistroEvento.objects.create(usuario=request.user, evento=entrada.idEvento)

            for entrada_actividad in entrada.actividades_incluidas.all():
                actividad = entrada_actividad.idActividad
                if not RegistroActividad.objects.filter(usuario=request.user, actividad=actividad).exists():
                    RegistroActividad.objects.create(usuario=request.user, actividad=actividad)
                actividad.nLugaresDisponibles -= 1
                actividad.save()
        else:
            entrada.nCantidad -= compra.nCantidad
            entrada.nVendidas += compra.nCantidad
            entrada.save()

            if compra.cupon:
                compra.cupon.nUsados += 1
                compra.cupon.save()

            for _ in range(compra.nCantidad):
                CodigoEntrada.objects.create(
                    compra=compra,
                    codigo=generar_codigo_unico()
                )

        enviar_correo_confirmacion(compra)

    return render(request, 'web/exitoso.html', {'titulo': "Pago", 'tipo': "compra"})

def generar_codigo_unico(longitud=10):
    caracteres = string.ascii_letters + string.digits + "!@#$%^&*()_+-=[]{}"
    while True:
        codigo = ''.join(random.choices(caracteres, k=longitud))
        if not CodigoEntrada.objects.filter(codigo=codigo).exists():
            return codigo

def pago_cancelado(request):
    return render(request, "web/pago_cancelado.html")

@login_required
def registro_gratuito(request, idEntrada):
    entrada = get_object_or_404(Entrada, idEntrada=idEntrada)

    if entrada.nCosto > 0:
        return redirect('index')

    if entrada.nCantidad <= 0:
        messages.error(request, "Esta entrada ya no tiene lugares disponibles")
        return redirect('evento_detalles', idEvento=entrada.idEvento.idEvento)

    evento = entrada.idEvento

    if not RegistroEvento.objects.filter(usuario=request.user, evento=evento).exists():
        RegistroEvento.objects.create(usuario=request.user, evento=evento)

    for entrada_actividad in entrada.actividades_incluidas.all():
        actividad = entrada_actividad.idActividad

        if not RegistroActividad.objects.filter(usuario=request.user, actividad=actividad).exists():
            RegistroActividad.objects.create(usuario=request.user, actividad=actividad)

        actividad.nLugaresDisponibles -= 1
        actividad.save()

    entrada.nCantidad -= 1
    entrada.nVendidas += 1
    entrada.save()

    enviar_correo_registro(request.user, entrada)

    return render(request, 'web/exitoso.html', {'titulo': "Registro", 'tipo': "registro"})

@login_required
def registro_por_cupon(request, idEntrada, compra_id):
    compra = get_object_or_404(CompraEntrada, idCompra=compra_id, entrada__idEntrada=idEntrada, usuario=request.user)
    entrada = compra.entrada

    if compra.status_pago == "pagado":
        return redirect("pago_exitoso", idEntrada=idEntrada, metodo_pago="gratuito_cuponado", compra_id=compra.idCompra)

    compra.status_pago = "pagado"
    compra.save()

    entrada.nCantidad -= 1
    entrada.nVendidas += 1
    entrada.save()

    if compra.cupon:
        compra.cupon.nUsados += 1
        compra.cupon.save()

    if not RegistroEvento.objects.filter(usuario=request.user, evento=entrada.idEvento).exists():
        RegistroEvento.objects.create(usuario=request.user, evento=entrada.idEvento)

    for entrada_actividad in entrada.actividades_incluidas.all():
        actividad = entrada_actividad.idActividad
        if not RegistroActividad.objects.filter(usuario=request.user, actividad=actividad).exists():
            RegistroActividad.objects.create(usuario=request.user, actividad=actividad)
        actividad.nLugaresDisponibles -= 1
        actividad.save()

    enviar_correo_confirmacion(compra)

    return render(request, 'web/exitoso.html', {'titulo': "Registro", 'tipo': "compra"})

@login_required
def registro_gratuito_evento(request, idEvento):
    evento = get_object_or_404(Evento, idEvento=idEvento)

    if not RegistroEvento.objects.filter(usuario=request.user, evento=evento).exists():
        RegistroEvento.objects.create(usuario=request.user, evento=evento)

    enviar_correo_registro_evento(request.user, evento)

    return render(request, 'web/exitoso.html', {'titulo': "Registro", 'tipo': "registro"})

def enviar_correo_registro(usuario, entrada):
    context = {"usuario": usuario, "entrada": entrada}
    html_content = render_to_string("web/email_registro.html", context)
    text_content = strip_tags(html_content)

    asunto = f"Confirmación de registro: {entrada.aNombre}"
    email = EmailMultiAlternatives(asunto, text_content, "confirmacion@registroclustertim.com", [usuario.email])
    email.attach_alternative(html_content, "text/html")
    email.send()

def enviar_correo_registro_evento(usuario, evento):
    context = {"usuario": usuario, "evento": evento}
    html_content = render_to_string("web/email_registro_evento.html", context)
    text_content = strip_tags(html_content)

    asunto = f"Confirmación de registro: {evento.aNombre}"
    email = EmailMultiAlternatives(asunto, text_content, "confirmacion@registroclustertim.com", [usuario.email])
    email.attach_alternative(html_content, "text/html")
    email.send()

@login_required
def pago_actividad(request, idActividad):
    actividad = get_object_or_404(Actividad, idActividad=idActividad)

    if actividad.nCosto <= 0:
        return redirect('registro_gratuito_actividad', idActividad=actividad.idActividad)

    if request.method == "POST":
        metodo_pago = request.POST.get("metodo_pago").lower()
        acompañantes = request.POST.getlist("acompañantes")

        acompañantes_str = ",".join(acompañantes)

        if metodo_pago == "paypal":
            return redirect(reverse("paypal_payment_actividad", args=[idActividad]) + f"?acompañantes={acompañantes_str}")
        elif metodo_pago == "stripe":
            return redirect(reverse("stripe_payment_actividad", args=[idActividad]) + f"?acompañantes={acompañantes_str}")
        elif metodo_pago == "openpay":
            return redirect(reverse("openpay_payment_actividad", args=[idActividad]) + f"?acompañantes={acompañantes_str}")

    return render(request, "web/pago_actividad.html", {
        "actividad": actividad,
        "metodos_pago": ["PayPal", "Stripe"],
        "permitir_acompañantes": actividad.lAcompañantes,
        "max_acompañantes": actividad.nAcompañantes
    })

@login_required
def registro_acompañantes_actividad(request, idActividad):
    actividad = get_object_or_404(Actividad, idActividad=idActividad)

    if actividad.nCosto > 0:
        return redirect('pago_actividad', idActividad=idActividad)

    if request.method == "POST":

        acompañantes = request.POST.getlist("acompañantes")

        return redirect(reverse("registro_gratuito_actividad", args=[idActividad]) + f"?acompañantes=" + ",".join(acompañantes))

    return render(request, "web/registro_gratuito_actividad.html", {
        "actividad": actividad,
        "max_acompañantes": actividad.nAcompañantes
    })

@login_required
def registro_gratuito_actividad(request, idActividad):
    actividad = get_object_or_404(Actividad, idActividad=idActividad)

    if actividad.nCosto > 0:
        return redirect('pago_actividad', idActividad=actividad.idActividad)

    acompañantes = request.GET.get("acompañantes", "").split(",")

    registro, creado = RegistroActividad.objects.get_or_create(usuario=request.user, actividad=actividad)

    for nombre in acompañantes:
        if nombre.strip() and not AcompañanteActividad.objects.filter(registro=registro, aNombre=nombre.strip()).exists():
            AcompañanteActividad.objects.create(registro=registro, aNombre=nombre.strip())

    actividad.nLugaresDisponibles -= (1 + len([n for n in acompañantes if n.strip()]))
    actividad.save()

    return render(request, 'web/exitoso.html', {'titulo': "Registro", 'tipo': "registro"})

@login_required
def paypal_payment_actividad(request, idActividad):
    actividad = get_object_or_404(Actividad, idActividad=idActividad)

    paypal_params = {
        "cmd": "_xclick",
        "business": settings.PAYPAL_RECEIVER_EMAIL,
        "amount": actividad.nCosto,
        "currency_code": "MXN",
        "item_name": actividad.aNombre,
        "invoice": f"INV-{actividad.idActividad}-{request.user.idUsuario}",
        "notify_url": request.build_absolute_uri(reverse("paypal-ipn")),
        "return": request.build_absolute_uri(reverse("pago_exitoso_actividad", args=[actividad.idActividad, "paypal"])),
        "cancel_return": request.build_absolute_uri(reverse("pago_cancelado")),
    }

    paypal_url = "https://www.sandbox.paypal.com/cgi-bin/webscr?" + urllib.parse.urlencode(paypal_params)

    return redirect(paypal_url)

@login_required
def stripe_payment_actividad(request, idActividad):
    actividad = get_object_or_404(Actividad, idActividad=idActividad)

    stripe.api_key = settings.STRIPE_SECRET_KEY

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "mxn",
                "product_data": {
                    "name": actividad.aNombre,
                },
                "unit_amount": int(actividad.nCosto * 100),
            },
            "quantity": 1,
        }],
        mode="payment",
        success_url=request.build_absolute_uri(reverse("pago_exitoso_actividad", args=[actividad.idActividad, "stripe"])),
        cancel_url=request.build_absolute_uri(reverse("pago_cancelado")),
    )

    return redirect(session.url)

@login_required
def openpay_payment_actividad(request, idActividad):
    actividad = get_object_or_404(Actividad, idActividad=idActividad)

    OPENPAY_URL = f"https://sandbox-api.openpay.mx/v1/{settings.OPENPAY_MERCHANT_ID}/charges"

    headers = {
        "Authorization": "Basic " + base64.b64encode(f"{settings.OPENPAY_PRIVATE_KEY}:".encode()).decode(),
        "Content-Type": "application/json"
    }

    payload = {
        "method": "card",
        "source_id": "tok_test_visa",
        "amount": float(actividad.nCosto),
        "currency": "MXN",
        "description": f"Pago por actividad: {actividad.aNombre}",
        "order_id": f"ORD-{actividad.idActividad}-{request.user.idUsuario}",
        "device_session_id": request.session.session_key,
        "customer": {
            "name": request.user.first_name,
            "last_name": request.user.last_name,
            "email": request.user.email,
        }
    }

    response = requests.post(OPENPAY_URL, json=payload, headers=headers)

    if response.status_code == 200:
        return redirect(reverse("pago_exitoso_actividad", args=[actividad.idActividad, "openpay"]))
    else:
        return redirect(reverse("pago_cancelado"))

@login_required
def pago_exitoso_actividad(request, idActividad, metodo_pago):
    actividad = get_object_or_404(Actividad, idActividad=idActividad)

    compra = CompraActividad.objects.create(
        usuario=request.user,
        actividad=actividad,
        metodo_pago=metodo_pago,
        monto_pago=actividad.nCosto,
        status_pago="pagado"
    )

    actividad.nLugaresDisponibles -= 1
    actividad.save()

    acompañantes = request.GET.get("acompañantes", "").split(",")

    registro, creado = RegistroActividad.objects.get_or_create(usuario=request.user, actividad=actividad)

    for nombre in acompañantes:
        if nombre.strip() and not AcompañanteActividad.objects.filter(registro=registro, aNombre=nombre.strip()).exists():
            AcompañanteActividad.objects.create(registro=registro, aNombre=nombre.strip())
            actividad.nLugaresDisponibles -= 1

    actividad.save()

    enviar_correo_confirmacion_actividad(compra)

    return render(request, 'web/exitoso.html', {'titulo': "Pago", 'tipo': "compra"})

def enviar_correo_confirmacion_actividad(compra):
    context = {"compra": compra}
    html_content = render_to_string("web/email_confirmacion_actividad.html", context)
    text_content = strip_tags(html_content)

    asunto = f"Confirmación de compra: {compra.actividad.aNombre}"
    email = EmailMultiAlternatives(asunto, text_content, "confirmacion@registroclustertim.com", [compra.usuario.email])
    email.attach_alternative(html_content, "text/html")
    email.send()

@login_required
def editar_acompañantes(request, idActividad):
    actividad = get_object_or_404(Actividad, idActividad=idActividad)
    registro = get_object_or_404(RegistroActividad, usuario=request.user, actividad=actividad)

    acompañantes_existentes = list(AcompañanteActividad.objects.filter(registro=registro).values_list('aNombre', flat=True))

    max_acompañantes = actividad.nAcompañantes

    if request.method == "POST":
        nuevos_nombres = request.POST.getlist('acompañantes')

        AcompañanteActividad.objects.filter(registro=registro).delete()

        for nombre in nuevos_nombres:
            if nombre.strip():
                AcompañanteActividad.objects.create(registro=registro, aNombre=nombre.strip())

        return redirect('evento_detalles', idEvento=actividad.idEvento.idEvento)

    return render(request, 'web/editar_acompañantes.html', {
        'actividad': actividad,
        'acompañantes': acompañantes_existentes + [''] * (max_acompañantes - len(acompañantes_existentes)),
        'max_acompañantes': max_acompañantes
    })

def pago_aportacion(request, idAportacion):
    aportacion = get_object_or_404(Aportacion, idAportacion=idAportacion, lActivo=True)

    if aportacion.eEstado == 'pagada':
        messages.error(request, "Aportación ya pagada anteriormente.")
        return redirect("evento_detalles", idEvento=aportacion.idEvento.idEvento)

    monto_final = aportacion.monto_pago

    if request.method == "POST":
        metodo_pago = request.POST.get("metodo_pago", "").strip().lower()

        if metodo_pago not in ["efectivo", "paypal", "stripe"]:
            messages.error(request, "Método de pago no válido.")
            return redirect("pago_aportacion", idAportacion=idAportacion)

        aportacion.metodo_pago = metodo_pago
        aportacion.save()

        if metodo_pago == "efectivo":
            enviar_correo_pago_efectivo_aportacion(aportacion)
            return redirect("pago_pendiente_aportacion", aportacion_id=aportacion.idAportacion)

        return redirect(reverse(f"{metodo_pago}_payment_aportacion", args=[aportacion.idAportacion]))

    metodos_pago = ["PayPal"]
    if monto_final >= 10:
        metodos_pago.append("Stripe")
    if DatosPagoEfectivoConfiguracion.objects.filter(lActivo=True).exists():
        metodos_pago.append("Efectivo")

    return render(request, "web/pago_aportacion.html", {
        "aportacion": aportacion,
        "monto_final": monto_final,
        "metodos_pago": metodos_pago
    })

def enviar_correo_pago_efectivo_aportacion(aportacion):
    datos = DatosPagoEfectivoConfiguracion.objects.filter(lActivo=True).first()
    if not datos:
        return

    context = {
        "aportacion": aportacion,
        "datos_pago": datos
    }
    html_content = render_to_string("web/email_pago_efectivo_aportacion.html", context)
    text_content = strip_tags(html_content)

    asunto = f"Pago pendiente de aportación: {aportacion.aNombre}"
    email = EmailMultiAlternatives(asunto, text_content, "confirmacion@registroclustertim.com", [aportacion.idAportador.aEmail])
    email.attach_alternative(html_content, "text/html")
    email.send()

def paypal_payment_aportacion(request, idAportacion):
    aportacion = get_object_or_404(Aportacion, idAportacion=idAportacion)

    paypal_params = {
        "cmd": "_xclick",
        "business": settings.PAYPAL_RECEIVER_EMAIL,
        "amount": f"{aportacion.monto_pago:.2f}",
        "currency_code": "MXN",
        "item_name": f"Aportación: {aportacion.aNombre}",
        "invoice": f"INV-APORT-{aportacion.idAportacion}",
        "notify_url": request.build_absolute_uri(reverse("paypal-ipn")),
        "return": request.build_absolute_uri(reverse("pago_exitoso_aportacion", args=[aportacion.idAportacion])),
        "cancel_return": request.build_absolute_uri(reverse("pago_cancelado")),
    }

    paypal_url = "https://www.paypal.com/cgi-bin/webscr?" + urllib.parse.urlencode(paypal_params)
    return redirect(paypal_url)

def stripe_payment_aportacion(request, idAportacion):
    aportacion = get_object_or_404(Aportacion, idAportacion=idAportacion)
    stripe.api_key = settings.STRIPE_SECRET_KEY

    if aportacion.monto_pago < 10:
        messages.error(request, "Stripe no permite pagos menores a $10.00 MXN.")
        return redirect("pago_aportacion", idAportacion=idAportacion)

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "mxn",
                "product_data": {
                    "name": f"Aportación: {aportacion.aNombre}",
                },
                "unit_amount": int(aportacion.monto_pago * 100),
            },
            "quantity": 1,
        }],
        mode="payment",
        success_url=request.build_absolute_uri(reverse("pago_exitoso_aportacion", args=[aportacion.idAportacion])),
        cancel_url=request.build_absolute_uri(reverse("pago_cancelado")),
    )

    return redirect(session.url)

def pago_exitoso_aportacion(request, idAportacion):
    aportacion = get_object_or_404(Aportacion, idAportacion=idAportacion)

    if aportacion.eEstado != 'pagada':
        aportacion.marcar_como_pagada()
        enviar_correo_confirmacion_aportacion(aportacion)

    return render(request, "web/exitoso_aportacion.html", {
        "titulo": "Aportación",
        "tipo": "aportación",
        "ultimo_evento_id": aportacion.idEvento.idEvento
    })

def pago_pendiente_aportacion(request, aportacion_id):
    aportacion = get_object_or_404(Aportacion, idAportacion=aportacion_id)

    return render(request, "web/pago_pendiente_aportacion.html", {
        "aportacion": aportacion,
        "titulo": "Aportación",
        "tipo": "registro"
    })

def enviar_correo_confirmacion_aportacion(aportacion):
    context = {"aportacion": aportacion}
    html_content = render_to_string("web/email_confirmacion_aportacion.html", context)
    text_content = strip_tags(html_content)

    asunto = f"Confirmación de aportación: {aportacion.aNombre}"
    email = EmailMultiAlternatives(asunto, text_content, "confirmacion@registroclustertim.com", [aportacion.idAportador.aEmail])
    email.attach_alternative(html_content, "text/html")
    email.send()

def enviar_correo_pago_efectivo_aportacion(aportacion):
    datos = DatosPagoEfectivoConfiguracion.objects.filter(lActivo=True).first()
    if not datos:
        return

    context = {
        "aportacion": aportacion,
        "datos_pago": datos
    }
    html_content = render_to_string("web/email_pago_efectivo_aportacion.html", context)
    text_content = strip_tags(html_content)

    asunto = f"Pago pendiente de aportación: {aportacion.aNombre}"
    email = EmailMultiAlternatives(asunto, text_content, "confirmacion@registroclustertim.com", [aportacion.idAportador.aEmail])
    email.attach_alternative(html_content, "text/html")
    email.send()
