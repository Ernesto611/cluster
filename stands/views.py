from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Stand, Producto, RegistroStand, CitaStand, HorarioCita, ArchivoStand
from usuarios.models import PermisoPersonalizado
from .forms import StandForm, ProductoForm, ArchivoStandForm
import os
from django.urls import reverse
from .decorators import role_required
from django.db.models import Q
from eventos.models import Evento
from datetime import datetime, timedelta, timezone as dt_timezone
from django.utils.timezone import make_aware
from django.views.decorators.http import require_POST
from utils.permisos import (
    permiso_o_superadmin_requerido,
    permiso_listado,
    permisos_de_usuario,
    tiene_permiso_en_alguna_categoria,
    get_eventos_por_categoria,
    get_stands_por_categoria,
    permiso_listado_cualquiera,
    tiene_accion_listar,
    tiene_permiso_representante,
    permiso_stands_acciones_o_representante,
    permiso_archivos_stand_accion_o_representante,
    es_super_administrador,
    permiso_productos_stand_accion_o_representante,
    permiso_producto_accion_o_representante
)
from django.db import transaction
from django.utils import timezone
import logging
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings

@login_required
@permiso_listado_cualquiera(['stands', 'archivos_stand', 'productos_stand'])
def listado(request):
    usuario = request.user
    q = request.GET.get("q")
    evento_id = request.GET.get("evento")

    permisos = set(permisos_de_usuario(usuario, 'stands') or [])
    permisos_archivos = set(permisos_de_usuario(usuario, 'archivos_stand') or [])
    permisos_productos = set(permisos_de_usuario(usuario, 'productos_stand') or [])

    es_rep_stands = tiene_permiso_representante(usuario, 'stands')
    if es_rep_stands:

        permisos.update(['agregar', 'editar', 'desactivar'])

    if getattr(usuario, 'tipo_usuario', '') == 'super_administrador':
        categorias_habilitadas = ['stands', 'archivos_stand', 'productos_stand']
    else:
        categorias_posibles = ['stands', 'archivos_stand', 'productos_stand']
        categorias_habilitadas = [
            cat for cat in categorias_posibles
            if tiene_accion_listar(permisos_de_usuario(usuario, cat))
        ]
        if not categorias_habilitadas:
            categorias_habilitadas = list(
                PermisoPersonalizado.objects
                .filter(usuario=usuario, categoria__in=categorias_posibles)
                .values_list('categoria', flat=True)
                .distinct()
            )

    stand_ids_permitidos = set()
    for cat in categorias_habilitadas:
        qs_cat = get_stands_por_categoria(usuario, cat).values_list('idStand', flat=True)
        stand_ids_permitidos.update(qs_cat)

    stands = Stand.objects.filter(idStand__in=stand_ids_permitidos)

    eventos_ids = list(stands.values_list('idEvento__idEvento', flat=True).distinct())
    eventos = Evento.objects.filter(idEvento__in=eventos_ids)

    if q:
        stands = stands.filter(Q(aNombre__icontains=q) | Q(nNumeroStand__icontains=q))

    if evento_id:
        stands = stands.filter(idEvento__idEvento=evento_id)

    return render(request, 'stands/listado.html', {
        'stands': stands,
        'eventos': eventos,
        'q': q or '',
        'evento_id': evento_id or '',

        'permisos': list(permisos),
        'permisos_archivos': list(permisos_archivos),
        'permisos_productos': list(permisos_productos),

        'es_rep_stands': es_rep_stands,
    })

@login_required
@permiso_stands_acciones_o_representante('agregar')
def agregar(request):
    usuario = request.user

    es_rep_stands = tiene_permiso_representante(usuario, 'stands')

    stands_visibles = get_stands_por_categoria(usuario, 'stands')

    alcance_stand = PermisoPersonalizado.objects.filter(
        usuario=usuario,
        categoria='stands',
        alcance='stand'
    ).exists()

    if alcance_stand:
        eventos_ids = stands_visibles.values_list('idEvento__idEvento', flat=True).distinct()
        eventos_permitidos = Evento.objects.filter(idEvento__in=eventos_ids)
    else:
        eventos_permitidos = get_eventos_por_categoria(usuario, 'stands')

    if request.method == 'POST':
        form = StandForm(
            request.POST, request.FILES,
            request=request,
            forzar_representante=es_rep_stands,
            usuario_autenticado=usuario
        )

        form.fields['idEvento'].queryset = eventos_permitidos

        if form.is_valid():
            form.save()
            messages.success(request, 'El stand ha sido creado correctamente.')
            return redirect('listado_stands')
        else:
            messages.error(request, 'Hubo un error al crear el stand. Revisa los campos.')
    else:
        form = StandForm(
            request=request,
            forzar_representante=es_rep_stands,
            usuario_autenticado=usuario
        )
        form.fields['idEvento'].queryset = eventos_permitidos

    return render(request, 'stands/agregar.html', {
        'form': form,
        'es_rep_stands': es_rep_stands,
    })

@login_required
@permiso_listado('stands')
def detalles(request, idStand):
    stand = get_object_or_404(Stand, idStand=idStand)
    productos = stand.productos.all()
    return render(request, 'stands/detalles.html', {'stand': stand, 'productos': productos})

@login_required
@permiso_stands_acciones_o_representante('editar')
def editar(request, idStand):
    usuario = request.user
    stand = get_object_or_404(Stand, idStand=idStand)

    stands_permitidos_qs = get_stands_por_categoria(usuario, 'stands')

    if getattr(usuario, 'tipo_usuario', '') != 'super_administrador':
        if not stands_permitidos_qs.filter(idStand=stand.idStand).exists():
            return redirect('acceso_restringido')

    es_rep_stands = tiene_permiso_representante(usuario, 'stands')
    soy_rep_de_este = es_rep_stands and (stand.representante_id == getattr(usuario, 'idUsuario', None))

    alcance_stand = PermisoPersonalizado.objects.filter(
        usuario=usuario, categoria='stands', alcance='stand'
    ).exists()

    if alcance_stand:
        ev_ids = list(
            stands_permitidos_qs.values_list('idEvento__idEvento', flat=True).distinct()
        )
        eventos_permitidos = Evento.objects.filter(idEvento__in=ev_ids)
    else:
        eventos_permitidos = get_eventos_por_categoria(usuario, 'stands')

    ev_ids_union = set(eventos_permitidos.values_list('idEvento', flat=True))
    ev_ids_union.add(stand.idEvento_id)
    eventos_permitidos = Evento.objects.filter(idEvento__in=ev_ids_union)

    forzar_representante = soy_rep_de_este and getattr(usuario, 'tipo_usuario', '') != 'super_administrador'

    if request.method == 'POST':
        form = StandForm(
            request.POST, request.FILES,
            instance=stand,
            request=request,
            forzar_representante=forzar_representante,
            usuario_autenticado=usuario
        )
        form.fields['idEvento'].queryset = eventos_permitidos

        if form.is_valid():
            form.save()
            messages.success(request, 'El stand ha sido actualizado correctamente.')
            return redirect('listado_stands')
        else:
            messages.error(request, 'Hubo un error al actualizar el stand. Revisa los campos.')
    else:
        form = StandForm(
            instance=stand,
            request=request,
            forzar_representante=forzar_representante,
            usuario_autenticado=usuario
        )
        form.fields['idEvento'].queryset = eventos_permitidos

    return render(request, 'stands/editar.html', {
        'form': form,
        'stand': stand,
        'es_rep_stands': es_rep_stands,
        'soy_rep_de_este': soy_rep_de_este,
    })

@login_required
@permiso_stands_acciones_o_representante('desactivar')
def alternar_estado(request, idStand):
    stand = get_object_or_404(Stand, idStand=idStand)
    if request.method == 'POST':
        stand.lActivo = not stand.lActivo
        stand.save()
        if stand.lActivo:
            messages.success(request, 'El stand se activó correctamente.')
        else:
            messages.success(request, 'El stand se desactivó correctamente.')
    return redirect('listado_stands')

@login_required
@role_required(["super_administrador"])
def eliminar(request, idStand):
    stand = get_object_or_404(Stand, idStand=idStand)

    if request.method == 'POST':
        stand.delete()
        messages.success(request, 'El stand ha sido eliminado correctamente.')
        return redirect('listado_stands')

    return render(request, 'stands/eliminar.html', {'stand': stand})

def obtener_stands_por_evento(request):
    evento_id = request.GET.get('evento_id')
    stands = Stand.objects.filter(idEvento_id=evento_id, lActivo=True).values('idStand', 'aNombre')
    return JsonResponse(list(stands), safe=False)

@login_required
@permiso_listado('registros_stands')
def listar_registros_stands(request):
    usuario = request.user
    es_super = getattr(usuario, 'tipo_usuario', '') == 'super_administrador'

    es_rep = (
        tiene_permiso_representante(usuario, 'stands') or
        PermisoPersonalizado.objects.filter(
            usuario=usuario, categoria='registros_stands', accion='representante'
        ).exists()
    )

    tiene_permiso_registros_no_rep = PermisoPersonalizado.objects.filter(
        usuario=usuario, categoria='registros_stands'
    ).exclude(accion='representante').exists()

    if es_super:
        stands_visibles = Stand.objects.all()
        es_rep_solo = False
    elif es_rep and not tiene_permiso_registros_no_rep:

        stands_visibles = Stand.objects.filter(representante=usuario)
        es_rep_solo = True
    else:

        stands_visibles = get_stands_por_categoria(usuario, 'registros_stands')
        es_rep_solo = False

    eventos_ids = stands_visibles.values_list('idEvento__idEvento', flat=True).distinct()
    eventos_visibles = Evento.objects.filter(idEvento__in=eventos_ids)

    registros = (
        RegistroStand.objects
        .select_related('usuario', 'stand', 'stand__idEvento')
        .filter(stand__in=stands_visibles)
    )

    q = (request.GET.get('q') or '').strip()
    evento_id = request.GET.get('evento')
    stand_id = request.GET.get('stand')

    if q:
        registros = registros.filter(
            Q(usuario__aNombre__icontains=q) |
            Q(usuario__aApellido__icontains=q) |
            Q(usuario__email__icontains=q)
        )

    if evento_id:
        stands_filtrados = stands_visibles.filter(idEvento_id=evento_id)
        registros = registros.filter(stand__in=stands_filtrados)

    if stand_id:

        if stands_visibles.filter(idStand=stand_id).exists():
            registros = registros.filter(stand_id=stand_id)
        else:
            registros = registros.none()

    return render(request, 'stands/registro_stands.html', {
        'registros': registros,
        'eventos': eventos_visibles,
        'stands': stands_visibles,
        'q': q,
        'evento_id': evento_id,
        'stand_id': stand_id,
        'es_rep_solo': es_rep_solo,
    })

@login_required
@permiso_listado('archivos_stand')
def gestionar_archivos_stand(request, idStand):
    stand = get_object_or_404(Stand, idStand=idStand)
    usuario = request.user

    es_super = getattr(usuario, 'tipo_usuario', '') == 'super_administrador'
    es_rep_del_stand = (
        tiene_permiso_representante(usuario, 'stands') and
        stand.representante_id == getattr(usuario, 'idUsuario', None)
    )

    stands_visibles_archivos = get_stands_por_categoria(usuario, 'archivos_stand')

    if not (es_super or es_rep_del_stand or stands_visibles_archivos.filter(idStand=stand.idStand).exists()):
        return redirect('acceso_restringido')

    permisos_archivos = set(permisos_de_usuario(usuario, 'archivos_stand') or [])
    puede_agregar    = es_super or ('agregar' in permisos_archivos) or es_rep_del_stand
    puede_editar     = es_super or ('editar' in permisos_archivos) or es_rep_del_stand
    puede_desactivar = es_super or ('desactivar' in permisos_archivos) or es_rep_del_stand
    puede_borrar     = es_super or ('borrar' in permisos_archivos) or es_rep_del_stand

    if request.method == "POST":
        if not puede_agregar:
            return redirect('acceso_restringido')

        form = ArchivoStandForm(request.POST, request.FILES)
        if form.is_valid():
            archivo = form.save(commit=False)
            archivo.stand = stand
            archivo.save()
            messages.success(request, "Archivo subido correctamente.")
            return redirect('gestionar_archivos_stand', idStand=stand.idStand)
        else:
            messages.error(request, "Hubo un error al subir el archivo.")
    else:
        form = ArchivoStandForm()

    archivos = stand.archivos.all()
    return render(request, "stands/gestionar_archivos.html", {
        "stand": stand,
        "form": form,
        "archivos": archivos,

        "permisos": list(permisos_archivos),

        "es_rep_del_stand": es_rep_del_stand,
        "puede_agregar": puede_agregar,
        "puede_editar": puede_editar,
        "puede_desactivar": puede_desactivar,
        "puede_borrar": puede_borrar,
    })

@require_POST
@login_required
@permiso_archivos_stand_accion_o_representante('editar')
def editar_archivo_stand(request, id_archivo):
    archivo = get_object_or_404(ArchivoStand, id=id_archivo)
    user = request.user

    if not es_super_administrador(user):
        es_rep = tiene_permiso_representante(user, 'stands') and (archivo.stand.representante_id == getattr(user, 'idUsuario', None))
        tiene_editar = PermisoPersonalizado.objects.filter(usuario=user, categoria='archivos_stand', accion='editar').exists()
        if not (es_rep or tiene_editar):
            return redirect('acceso_restringido')

    nuevo_titulo = (request.POST.get("titulo") or "").strip()
    if nuevo_titulo:
        archivo.titulo = nuevo_titulo
        archivo.save()
        messages.success(request, "Título del archivo actualizado correctamente.")
    else:
        messages.error(request, "El título no puede estar vacío.")
    return redirect('gestionar_archivos_stand', idStand=archivo.stand.idStand)

@login_required
@permiso_archivos_stand_accion_o_representante('desactivar')
def alternar_estado_archivo(request, id):
    archivo = get_object_or_404(ArchivoStand, id=id)

    if request.method == 'POST':
        archivo.lActivo = not archivo.lActivo
        archivo.save()
        messages.success(request, 'El archivo se activó correctamente.' if archivo.lActivo else 'El archivo se desactivó correctamente.')

    return redirect('gestionar_archivos_stand', idStand=archivo.stand.idStand)

@require_POST
@login_required
@permiso_archivos_stand_accion_o_representante('borrar')
def eliminar_archivo_stand(request, id_archivo):
    archivo = get_object_or_404(ArchivoStand, id=id_archivo)
    stand_id = archivo.stand.idStand

    if archivo.archivo:
        archivo.archivo.delete(save=False)
    archivo.delete()
    messages.success(request, "Archivo eliminado correctamente.")

    return redirect('gestionar_archivos_stand', idStand=stand_id)

@login_required
@permiso_listado('productos_stand')
def listado_productos(request, idStand):
    usuario = request.user
    q = request.GET.get("q", "").strip()
    stand = get_object_or_404(Stand, idStand=idStand)

    es_super = getattr(usuario, 'tipo_usuario', '') == 'super_administrador'
    es_rep_del_stand = (
        tiene_permiso_representante(usuario, 'stands') and
        stand.representante_id == getattr(usuario, 'idUsuario', None)
    )
    stands_visibles_productos = get_stands_por_categoria(usuario, 'productos_stand')

    if not (es_super or es_rep_del_stand or stands_visibles_productos.filter(idStand=stand.idStand).exists()):
        return redirect('acceso_restringido')

    permisos_productos = set(permisos_de_usuario(usuario, 'productos_stand') or [])
    puede_agregar    = es_super or ('agregar' in permisos_productos) or es_rep_del_stand
    puede_editar     = es_super or ('editar' in permisos_productos) or es_rep_del_stand
    puede_desactivar = es_super or ('desactivar' in permisos_productos) or es_rep_del_stand
    puede_borrar     = es_super or ('borrar' in permisos_productos) or es_rep_del_stand

    productos = stand.productos.all()
    if q:
        productos = productos.filter(Q(aNombre__icontains=q))

    return render(request, 'stands/listado_productos.html', {
        'stand': stand,
        'productos': productos,
        'q': q,

        'permisos': list(permisos_productos),

        'es_rep_del_stand': es_rep_del_stand,
        'puede_agregar': puede_agregar,
        'puede_editar': puede_editar,
        'puede_desactivar': puede_desactivar,
        'puede_borrar': puede_borrar,
    })

@login_required
@permiso_productos_stand_accion_o_representante('agregar')
def agregar_producto(request, idStand):
    usuario = request.user
    stand = get_object_or_404(Stand, idStand=idStand)

    es_super = es_super_administrador(usuario)
    es_rep_del_stand = tiene_permiso_representante(usuario, 'stands') and (
        stand.representante_id == getattr(usuario, 'idUsuario', None)
    )
    stands_visibles_productos = get_stands_por_categoria(usuario, 'productos_stand')

    if not (es_super or es_rep_del_stand or stands_visibles_productos.filter(idStand=stand.idStand).exists()):
        return redirect('acceso_restringido')

    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES)
        if form.is_valid():
            producto = form.save(commit=False)
            producto.idStand = stand
            producto.save()
            messages.success(request, 'El producto ha sido agregado correctamente.')
            return redirect('listado_productos', idStand=idStand)
        else:
            messages.error(request, 'Hubo un error al agregar el producto. Revisa los campos.')
    else:
        form = ProductoForm()

    return render(request, 'stands/agregar_producto.html', {
        'form': form,
        'stand': stand,
        'es_rep_del_stand': es_rep_del_stand,
    })

@login_required
@permiso_listado('productos_stand')
def detalles_producto(request, idProducto):
    producto = get_object_or_404(Producto, idProducto=idProducto)
    return render(request, 'stands/detalles_producto.html', {'producto': producto})

@login_required
@permiso_producto_accion_o_representante('editar')
def editar_producto(request, idProducto):
    producto = get_object_or_404(Producto, idProducto=idProducto)

    user = request.user
    if not es_super_administrador(user):
        es_rep = tiene_permiso_representante(user, 'stands') and (
            producto.idStand.representante_id == getattr(user, 'idUsuario', None)
        )

    ruta_imagen_anterior = producto.aImagen.path if producto.aImagen else None

    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES, instance=producto)
        if form.is_valid():

            if 'aImagen' in request.FILES:
                if ruta_imagen_anterior and os.path.isfile(ruta_imagen_anterior):
                    try:
                        os.remove(ruta_imagen_anterior)
                    except Exception as e:

                        print(f"Error al eliminar la imagen anterior: {e}")

            form.save()
            messages.success(request, 'El producto ha sido actualizado correctamente.')
            return redirect('listado_productos', idStand=producto.idStand.idStand)
        else:
            messages.error(request, 'Hubo un error al actualizar el producto. Revisa los campos.')
    else:
        form = ProductoForm(instance=producto)

    return render(request, 'stands/editar_producto.html', {
        'form': form,
        'producto': producto,
    })

@login_required
@permiso_producto_accion_o_representante('desactivar')
def alternar_estado_producto(request, idProducto):
    producto = get_object_or_404(Producto, idProducto=idProducto)
    if request.method == 'POST':
        producto.lActivo = not producto.lActivo
        producto.save()
        messages.success(request, 'El producto se activó correctamente.' if producto.lActivo else 'El producto se desactivó correctamente.')
    return redirect('listado_productos', idStand=producto.idStand.idStand)

@login_required
@require_POST
@permiso_producto_accion_o_representante('borrar')
def eliminar_producto(request, idProducto):
    producto = get_object_or_404(Producto, idProducto=idProducto)
    stand_id = producto.idStand.idStand

    if producto.aImagen:
        try:
            if os.path.isfile(producto.aImagen.path):
                os.remove(producto.aImagen.path)
        except Exception:
            pass
    producto.delete()
    messages.success(request, 'El producto ha sido eliminado correctamente.')
    return redirect('listado_productos', idStand=stand_id)

@login_required
@permiso_listado('citas')
def listado_citas(request):
    usuario = request.user
    q = request.GET.get("q")
    stand_id = request.GET.get("stand")
    status = request.GET.get("status")
    stands = get_stands_por_categoria(usuario, 'citas')

    citas = CitaStand.objects.filter(idStand__in=stands)

    if q:
        citas = citas.filter(
            Q(idUsuario__aNombre__icontains=q) |
            Q(idUsuario__email__icontains=q)
        )

    if stand_id:
        citas = citas.filter(idStand__idStand=stand_id)

    if status:
        citas = citas.filter(aStatus=status)

    return render(request, "stands/listado_citas.html", {
        "citas": citas,
        "stands": stands,
        "q": q,
        "stand_id": stand_id,
        "status": status,
    })

logger = logging.getLogger(__name__)

@login_required
@permiso_listado('citas')
def detalles_cita(request, idCita):
    cita = get_object_or_404(
        CitaStand.objects.select_related('idStand', 'idUsuario'),
        idCita=idCita
    )

    stands_qs = get_stands_por_categoria(request.user, 'citas')
    try:

        if hasattr(stands_qs, 'filter'):
            puede_ver = stands_qs.filter(pk=cita.idStand_id).exists()
        else:
            ids = {s.pk if hasattr(s, 'pk') else int(s) for s in stands_qs}
            puede_ver = cita.idStand_id in ids
    except Exception as e:
        logger.exception("Error evaluando permisos de stands: %s", e)
        puede_ver = False

    if not puede_ver:
        messages.error(request, "No tienes permisos para ver esta cita.")
        return redirect("listado_citas")

    all_choices = dict(CitaStand._meta.get_field('aStatus').choices)
    status_choices = [(v, l) for v, l in all_choices.items() if v not in ("pendiente", "completada")]

    if request.method == "POST":
        nuevo_status = (request.POST.get("status") or "").strip()
        nueva_nota = (request.POST.get("nota") or "").strip()

        if nuevo_status and nuevo_status not in all_choices:
            messages.error(request, "Estado inválido.")
            return redirect("detalles_cita", idCita=cita.idCita)

        old_status = cita.aStatus

        if old_status == "completada":
            messages.info(request, "Esta cita ya fue completada y no puede modificarse.")
            return redirect("detalles_cita", idCita=cita.idCita)

        if nuevo_status and nuevo_status != "pendiente":
            cita.aStatus = nuevo_status

        cita.aNotas = nueva_nota
        cita.save(update_fields=["aStatus", "aNotas"])

        if old_status != "aceptada" and cita.aStatus == "aceptada":
            cita_id = cita.idCita
            transaction.on_commit(lambda: enviar_correo_cita_aceptada(cita_id))

        messages.success(request, "Cita actualizada correctamente.")
        return redirect("listado_citas")

    return render(request, "stands/detalles_cita.html", {
        "cita": cita,
        "status_choices": status_choices,
    })

def enviar_correo_cita_aceptada(id_cita: int):

    try:
        cita = CitaStand.objects.select_related('idStand', 'idUsuario').get(pk=id_cita)
    except CitaStand.DoesNotExist:
        logging.warning("Cita %s no encontrada al enviar correo de aceptación.", id_cita)
        return

    enlace = f"https://eventos.anadicmexico.mx/{cita.idStand_id}/detalles_stand/"

    context = {
        "cita": cita,
        "enlace_pago": enlace,
    }

    html_content = render_to_string("stands/email_cita_aceptada.html", context)
    text_content = strip_tags(html_content)

    asunto = f"Tu cita con {cita.idStand.aNombre} ha sido aceptada"
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "confirmacion@eventos.anadicmexico.mx")
    to_emails = [cita.idUsuario.email]

    try:
        email = EmailMultiAlternatives(
            subject=asunto,
            body=text_content,
            from_email=from_email,
            to=to_emails,
            reply_to=[from_email],
        )
        email.attach_alternative(html_content, "text/html")
        sent = email.send(fail_silently=False)
        logging.info("Correo de cita aceptada (cita=%s) enviado a %s. sent=%s",
                     cita.pk, to_emails, sent)
    except Exception as e:
        logging.exception("Fallo enviando correo de aceptación (cita=%s): %s", cita.pk, e)

def _parse_datetime_local(value: str):

    if not value:
        return None
    try:
        naive = datetime.fromisoformat(value)
    except ValueError:
        naive = datetime.strptime(value, "%Y-%m-%dT%H:%M")
    return timezone.make_aware(naive, timezone.get_current_timezone())

def _parse_date(value: str):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except Exception:
        return None

def _parse_time(value: str):
    try:
        return datetime.strptime(value, "%H:%M").time()
    except Exception:
        return None

def _aware_combine(d, t):
    naive = datetime.combine(d, t)
    return timezone.make_aware(naive, timezone.get_current_timezone())

def _to_utc(dt):

    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    return dt.astimezone(dt_timezone.utc)

@login_required
@permiso_listado('horarios_citas')
def gestionar_horarios_citas(request):
    usuario = request.user
    stand_id = request.GET.get("stand")

    stands = get_stands_por_categoria(usuario, 'horarios_citas').filter(lActivo=True)
    stand = stands.filter(idStand=stand_id).first() if stand_id else stands.first()

    if not stand:
        messages.error(request, "No hay stands disponibles para gestión de horarios de citas.")
        return redirect("administracion_redirect")

    if request.method == "POST" and "nuevo_horario" in request.POST:
        nueva_fecha_str = request.POST.get("fFechaHora")
        if not nueva_fecha_str:
            messages.error(request, "Debes proporcionar fecha/hora.")
            return redirect(f"{request.path}?stand={stand.idStand}")

        nueva_fecha = _parse_datetime_local(nueva_fecha_str)
        if not nueva_fecha:
            messages.error(request, "Fecha/hora inválida.")
            return redirect(f"{request.path}?stand={stand.idStand}")

        obj, created = HorarioCita.objects.get_or_create(idStand=stand, fFechaHora=nueva_fecha)
        if created:
            messages.success(request, "Horario agregado correctamente.")
        else:
            messages.warning(request, "Ese horario ya existe para este stand.")
        return redirect(f"{request.path}?stand={stand.idStand}")

    if request.method == "POST" and "eliminar_horario" in request.POST:
        horario_id = request.POST.get("idHorario")
        HorarioCita.objects.filter(idHorario=horario_id, idStand=stand).delete()
        messages.success(request, "Horario eliminado.")
        return redirect(f"{request.path}?stand={stand.idStand}")

    if request.method == "POST" and "crear_recurrente" in request.POST:
        inicio = _parse_datetime_local(request.POST.get("fInicio"))
        fin = _parse_datetime_local(request.POST.get("fFin"))
        try:
            intervalo = int(request.POST.get("intervalo_minutos") or "0")
        except ValueError:
            intervalo = 0

        if not inicio or not fin:
            messages.error(request, "Debes proporcionar inicio y fin.")
            return redirect(f"{request.path}?stand={stand.idStand}")
        if fin <= inicio:
            messages.error(request, "La fecha/hora de fin debe ser mayor a la de inicio.")
            return redirect(f"{request.path}?stand={stand.idStand}")
        if intervalo <= 0 or intervalo > 1440:
            messages.error(request, "El intervalo en minutos debe estar entre 1 y 1440.")
            return redirect(f"{request.path}?stand={stand.idStand}")

        delta = timedelta(minutes=intervalo)

        last_start = fin - delta

        existentes_qs = HorarioCita.objects.filter(
            idStand=stand,
            fFechaHora__gte=inicio,
            fFechaHora__lt=fin,
        ).values_list('fFechaHora', flat=True)
        existentes_utc = set(_to_utc(dt) for dt in existentes_qs)

        a_crear = []
        generados = 0

        slot = inicio
        while slot <= last_start:
            generados += 1
            if _to_utc(slot) not in existentes_utc:
                a_crear.append(HorarioCita(idStand=stand, fFechaHora=slot))
            slot += delta

        if len(a_crear) > 5000:
            messages.error(request, f"El rango generaría {len(a_crear)} horarios. Reduce el rango o aumenta el intervalo.")
            return redirect(f"{request.path}?stand={stand.idStand}")

        pre_count = HorarioCita.objects.filter(
            idStand=stand,
            fFechaHora__gte=inicio,
            fFechaHora__lt=fin,
        ).count()

        if a_crear:
            HorarioCita.objects.bulk_create(a_crear, ignore_conflicts=True)

        post_count = HorarioCita.objects.filter(
            idStand=stand,
            fFechaHora__gte=inicio,
            fFechaHora__lt=fin,
        ).count()

        creados = max(0, post_count - pre_count)
        omitidos = max(0, generados - creados)
        msg = f"Generados {creados} horarios."
        if omitidos:
            msg += f" Omitidos por duplicado: {omitidos}."
        messages.success(request, msg)
        return redirect(f"{request.path}?stand={stand.idStand}")

    if request.method == "POST" and "crear_recurrente_dias" in request.POST:
        fecha_inicio = _parse_date(request.POST.get("fecha_inicio"))
        fecha_fin = _parse_date(request.POST.get("fecha_fin"))
        hora_inicio = _parse_time(request.POST.get("hora_inicio"))
        hora_fin = _parse_time(request.POST.get("hora_fin"))

        dias_sel = request.POST.getlist("dias")
        dias_semana = {int(d) for d in dias_sel if d.isdigit()} if dias_sel else set(range(7))

        try:
            intervalo = int(request.POST.get("intervalo_minutos") or "0")
        except ValueError:
            intervalo = 0

        if not fecha_inicio or not fecha_fin or not hora_inicio or not hora_fin:
            messages.error(request, "Debes proporcionar rango de fechas y horas.")
            return redirect(f"{request.path}?stand={stand.idStand}")
        if fecha_fin < fecha_inicio:
            messages.error(request, "La fecha final debe ser mayor o igual a la inicial.")
            return redirect(f"{request.path}?stand={stand.idStand}")
        if intervalo <= 0 or intervalo > 1440:
            messages.error(request, "El intervalo en minutos debe estar entre 1 y 1440.")
            return redirect(f"{request.path}?stand={stand.idStand}")

        delta = timedelta(minutes=intervalo)

        overall_start = _aware_combine(fecha_inicio, hora_inicio)
        overall_end = _aware_combine(fecha_fin, hora_fin)

        existentes_qs = HorarioCita.objects.filter(
            idStand=stand,
            fFechaHora__gte=overall_start,
            fFechaHora__lt=overall_end,
        ).values_list('fFechaHora', flat=True)
        existentes_utc = set(_to_utc(dt) for dt in existentes_qs)

        a_crear = []
        generados = 0
        dias_invalidos = 0

        pre_count = HorarioCita.objects.filter(
            idStand=stand,
            fFechaHora__gte=overall_start,
            fFechaHora__lt=overall_end,
        ).count()

        dia_actual = fecha_inicio
        while dia_actual <= fecha_fin:
            if dia_actual.weekday() in dias_semana:
                day_start = _aware_combine(dia_actual, hora_inicio)
                day_end = _aware_combine(dia_actual, hora_fin)

                if day_end <= day_start:
                    dias_invalidos += 1
                else:
                    last_start = day_end - delta
                    slot = day_start
                    while slot <= last_start:
                        generados += 1
                        if _to_utc(slot) not in existentes_utc:
                            a_crear.append(HorarioCita(idStand=stand, fFechaHora=slot))
                        slot += delta
            dia_actual += timedelta(days=1)

        if len(a_crear) > 5000:
            messages.error(request, f"El rango generaría {len(a_crear)} horarios. Reduce el rango o aumenta el intervalo.")
            return redirect(f"{request.path}?stand={stand.idStand}")

        if a_crear:
            HorarioCita.objects.bulk_create(a_crear, ignore_conflicts=True)

        post_count = HorarioCita.objects.filter(
            idStand=stand,
            fFechaHora__gte=overall_start,
            fFechaHora__lt=overall_end,
        ).count()

        creados = max(0, post_count - pre_count)
        omitidos = max(0, generados - creados)

        msg = f"Generados {creados} horarios"
        if omitidos:
            msg += f". Omitidos por duplicado: {omitidos}"
        if dias_invalidos:
            msg += f". Días con horario inválido (fin ≤ inicio): {dias_invalidos}"
        msg += "."
        (messages.success if creados else messages.info)(request, msg)

        return redirect(f"{request.path}?stand={stand.idStand}")

    horarios = HorarioCita.objects.filter(idStand=stand).order_by('fFechaHora')

    return render(request, "stands/gestionar_horarios.html", {
        "stands": stands,
        "stand_actual": stand,
        "horarios": horarios,
    })
