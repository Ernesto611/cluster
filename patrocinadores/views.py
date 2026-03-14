from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Patrocinador
from .forms import PatrocinadorForm
from stands.forms import StandForm
import os
import logging
from .decorators import role_required
from django.db.models import Q
from utils.permisos import (
    permiso_o_superadmin_requerido,
    permiso_listado,
    permisos_de_usuario,
    tiene_permiso_en_alguna_categoria,
    get_eventos_por_categoria,
    get_actividades_por_categoria
)

logger = logging.getLogger(__name__)

@login_required
@permiso_listado('patrocinadores')
def listado(request):
    q = request.GET.get("q")

    usuario = request.user
    permisos = permisos_de_usuario(usuario, 'patrocinadores')
    permisos_archivos = permisos_de_usuario(usuario, 'archivos_stand')
    permisos_productos = permisos_de_usuario(usuario, 'productos_stand')
    eventos = get_eventos_por_categoria(usuario, 'patrocinadores')
    eventos_ids = eventos.values_list('idEvento', flat=True).distinct()
    patrocinadores = Patrocinador.objects.filter(idEvento__in=eventos_ids)

    if q:
        patrocinadores = patrocinadores.filter(
            Q(idUsuario__aNombre__icontains=q) |
            Q(idUsuario__aApellido__icontains=q) |
            Q(idUsuario__email__icontains=q) |
            Q(aTelefono__icontains=q) |
            Q(idStand__aNombre__icontains=q) |
            Q(idStand__nNumeroStand__icontains=q)
        )

    return render(request, 'patrocinadores/listado.html', {
        'patrocinadores': patrocinadores,
        'q': q,
        'permisos': permisos,
        'permisos_archivos': permisos_archivos,
        'permisos_productos': permisos_productos,
    })

@login_required
@permiso_o_superadmin_requerido('patrocinadores', 'agregar')
def agregar(request):
    usuario = request.user
    eventos_disponibles = get_eventos_por_categoria(usuario, 'patrocinadores')

    if request.method == 'POST':
        post_data = request.POST.copy()

        for red, url in {
            'aFacebook': 'https://www.facebook.com/',
            'aInstagram': 'https://www.instagram.com/',
            'aTwitter': 'https://twitter.com/'
        }.items():
            if post_data.get(red):
                post_data[red] = url + post_data[red]

        form = PatrocinadorForm(post_data, request.FILES, eventos=eventos_disponibles)
        stand_form = StandForm(request.POST, request.FILES, instance=stand, request=request) if post_data.get('tiene_stand') else None

        if form.is_valid() and (not stand_form or stand_form.is_valid()):
            patrocinador = form.save()

            if stand_form:
                stand = stand_form.save(commit=False)
                stand.idEvento = patrocinador.idEvento
                stand.save()
                patrocinador.idStand = stand
                patrocinador.save()

            messages.success(request, 'El patrocinador ha sido creado correctamente.')
            return redirect('listado_patrocinadores')
        else:
            messages.error(request, 'Hubo un error al crear el patrocinador.')
    else:
        form = PatrocinadorForm(eventos=eventos_disponibles)
        stand_form = StandForm()

    return render(request, 'patrocinadores/agregar.html', {
        'form': form,
        'stand_form': stand_form
    })

@login_required
@permiso_o_superadmin_requerido('patrocinadores', 'editar')
def editar(request, idPatrocinador):
    usuario = request.user
    patrocinador = get_object_or_404(Patrocinador, idPatrocinador=idPatrocinador)
    stand = patrocinador.idStand
    eventos_disponibles = get_eventos_por_categoria(usuario, 'patrocinadores')

    if request.method == 'POST':
        post_data = request.POST.copy()

        for red, url in {
            'aFacebook': 'https://www.facebook.com/',
            'aInstagram': 'https://www.instagram.com/',
            'aTwitter': 'https://twitter.com/'
        }.items():
            if post_data.get(red):
                post_data[red] = url + post_data[red]

        form = PatrocinadorForm(post_data, request.FILES, instance=patrocinador, eventos=eventos_disponibles)
        stand_form = StandForm(request.POST, request.FILES, instance=stand, request=request) if post_data.get('tiene_stand') else None

        if form.is_valid() and (not stand_form or stand_form.is_valid()):
            patrocinador = form.save(commit=False)

            if not patrocinador.idEvento:
                messages.error(request, "Debe seleccionar un evento para el patrocinador.")
                return render(request, 'patrocinadores/editar.html', {
                    'form': form, 'stand_form': stand_form, 'patrocinador': patrocinador
                })

            if post_data.get('tiene_stand'):
                if stand_form:
                    stand = stand_form.save(commit=False)
                    stand.idEvento = patrocinador.idEvento
                    stand.save()
                    patrocinador.idStand = stand
            else:
                if stand:
                    stand.delete()
                    patrocinador.idStand = None

            patrocinador.save()
            messages.success(request, 'El patrocinador ha sido actualizado correctamente.')
            return redirect('listado_patrocinadores')
        else:
            messages.error(request, 'Hubo un error al actualizar el patrocinador. Revisa los campos.')
    else:
        def extract_username(url, domain):
            return url[len(domain):] if url and url.startswith(domain) else url

        form = PatrocinadorForm(instance=patrocinador, eventos=eventos_disponibles, initial={
            'aFacebook': extract_username(patrocinador.aFacebook, 'https://www.facebook.com/'),
            'aInstagram': extract_username(patrocinador.aInstagram, 'https://www.instagram.com/'),
            'aTwitter': extract_username(patrocinador.aTwitter, 'https://twitter.com/'),
        })
        stand_form = StandForm(instance=stand) if stand else StandForm()

    return render(request, 'patrocinadores/editar.html', {
        'form': form,
        'stand_form': stand_form,
        'patrocinador': patrocinador
    })

@login_required
@role_required(["super_administrador"])
def eliminar(request, idPatrocinador):
    patrocinador = get_object_or_404(Patrocinador, idPatrocinador=idPatrocinador)
    if request.method == 'POST':
        if patrocinador.aFoto and os.path.isfile(patrocinador.aFoto.path):
            os.remove(patrocinador.aFoto.path)
        patrocinador.delete()
        messages.success(request, 'El patrocinador se eliminó correctamente.')
        return redirect('listado_patrocinadores')
    return redirect('detalle_patrocinador', idPatrocinador=idPatrocinador)

@login_required
@permiso_o_superadmin_requerido('patrocinadores', 'desactivar')
def alternar_estado(request, idPatrocinador):
    patrocinador = get_object_or_404(Patrocinador, idPatrocinador=idPatrocinador)
    if request.method == 'POST':
        patrocinador.lActivo = not patrocinador.lActivo
        patrocinador.save()
        if patrocinador.lActivo:
            messages.success(request, 'El patrocinador se activó correctamente.')
        else:
            messages.success(request, 'El patrocinador se desactivó correctamente.')
    return redirect('listado_patrocinadores')
