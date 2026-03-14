from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from actividades.models import Actividad
from .decorators import role_required
from .forms import ExpositorForm, ArchivoExpositorForm
from .models import Expositor, ExpositorActividad, ArchivoExpositor
from utils.permisos import (
    permiso_o_superadmin_requerido,
    permiso_listado,
    permisos_de_usuario,
    tiene_permiso_en_alguna_categoria,
    get_actividades_por_categoria
)

@login_required
@permiso_listado('conferencistas')
def listado(request):
    usuario = request.user
    permisos = permisos_de_usuario(usuario, 'conferencistas')
    q = request.GET.get("q")

    expositores = Expositor.objects.all()

    if q:
        expositores = expositores.filter(
            Q(idUsuario__aNombre__icontains=q) |
            Q(idUsuario__aApellido__icontains=q) |
            Q(idUsuario__email__icontains=q) |
            Q(aTelefono__icontains=q)
        )

    return render(request, 'expositores/listado.html', {
        'expositores': expositores,
        'q': q,
        'permisos': permisos,
    })

@login_required
@permiso_o_superadmin_requerido('conferencistas', 'agregar')
def agregar(request):
    if request.method == 'POST':
        post_data = request.POST.copy()

        if post_data.get('aFacebook'):
            post_data['aFacebook'] = 'https://www.facebook.com/' + post_data['aFacebook']
        if post_data.get('aInstagram'):
            post_data['aInstagram'] = 'https://www.instagram.com/' + post_data['aInstagram']
        if post_data.get('aTwitter'):
            post_data['aTwitter'] = 'https://twitter.com/' + post_data['aTwitter']

        form = ExpositorForm(post_data, request.FILES)

        if form.is_valid():
            expositor = form.save()
            messages.success(request, 'El conferencista ha sido creado correctamente.')
            return redirect('asignar_actividades_expositor', expositor.idExpositor)
        else:
            messages.error(request, 'Hubo un error al crear el conferencista. Revisa los campos.')
    else:
        form = ExpositorForm()

    return render(request, 'expositores/agregar.html', {'form': form})

@login_required
@permiso_o_superadmin_requerido('conferencistas', 'asignar_actividades')
def asignar_actividades_expositor(request, id_expositor):
    expositor = get_object_or_404(Expositor, idExpositor=id_expositor)
    usuario = request.user
    actividades_disponibles = get_actividades_por_categoria(usuario, 'conferencistas').filter(lActivo=True)

    actividades_asignadas = ExpositorActividad.objects.filter(
        idExpositor=expositor
    ).values_list('idActividad', flat=True)

    if request.method == 'POST':
        actividades_ids = list(map(int, request.POST.getlist('actividades')))

        ExpositorActividad.objects.filter(
            idExpositor=expositor,
            idActividad__in=actividades_disponibles
        ).delete()

        for actividad_id in actividades_ids:
            actividad = get_object_or_404(Actividad, idActividad=actividad_id)
            if actividad in actividades_disponibles:
                ExpositorActividad.objects.create(idExpositor=expositor, idActividad=actividad)

        messages.success(request, "Actividades asignadas correctamente.")
        return redirect('listado_expositores')

    return render(request, 'expositores/asignar_actividades.html', {
        'expositor': expositor,
        'actividades': actividades_disponibles,
        'actividades_asignadas': list(actividades_asignadas)
    })

@login_required
@permiso_listado('conferencistas')
def detalles(request, idExpositor):
    expositor = get_object_or_404(Expositor, idExpositor=idExpositor)
    return render(request, 'expositores/detalles.html', {'expositor': expositor})

@login_required
@permiso_o_superadmin_requerido('conferencistas', 'editar')
def editar(request, idExpositor):
    expositor = get_object_or_404(Expositor, idExpositor=idExpositor)

    if request.method == 'POST':
        post_data = request.POST.copy()

        if post_data.get('aFacebook'):
            post_data['aFacebook'] = 'https://www.facebook.com/' + post_data['aFacebook']
        if post_data.get('aInstagram'):
            post_data['aInstagram'] = 'https://www.instagram.com/' + post_data['aInstagram']
        if post_data.get('aTwitter'):
            post_data['aTwitter'] = 'https://twitter.com/' + post_data['aTwitter']

        form = ExpositorForm(post_data, request.FILES, instance=expositor)

        if form.is_valid():
            form.save()
            messages.success(request, 'El expositor ha sido actualizado correctamente.')
            return redirect('listado_expositores')
        else:
            messages.error(request, 'Hubo un error al actualizar el expositor.')
    else:
        def extract_username(url, domain):
            if url and url.startswith(domain):
                return url[len(domain):]
            return url

        initial_data = {
            'aFacebook': extract_username(expositor.aFacebook, 'https://www.facebook.com/'),
            'aInstagram': extract_username(expositor.aInstagram, 'https://www.instagram.com/'),
            'aTwitter': extract_username(expositor.aTwitter, 'https://twitter.com/'),
        }

        form = ExpositorForm(instance=expositor, initial=initial_data)

    return render(request, 'expositores/editar.html', {
        'form': form,
        'expositor': expositor
    })

@login_required
@role_required(["super_administrador"])
def eliminar(request, idExpositor):
    expositor = get_object_or_404(Expositor, idExpositor=idExpositor)
    usuario = expositor.idUsuario
    expositor.delete()
    usuario.delete()

    messages.success(request, 'El expositor y su usuario han sido eliminados correctamente.')
    return redirect('listado_expositores')

@login_required
@permiso_listado('archivos_conferencista')
def gestionar_archivos_expositor(request, idExpositor):
    usuario = request.user
    permisos = permisos_de_usuario(usuario, 'archivos_conferencista')
    expositor = get_object_or_404(Expositor, idExpositor=idExpositor)

    if request.method == "POST":
        form = ArchivoExpositorForm(request.POST, request.FILES)
        if form.is_valid():
            archivo = form.save(commit=False)
            archivo.expositor = expositor
            archivo.save()
            messages.success(request, "Archivo subido correctamente.")
            return redirect('gestionar_archivos_expositor', idExpositor=expositor.idExpositor)
        else:
            messages.error(request, "Hubo un error al subir el archivo.")
    else:
        form = ArchivoExpositorForm()

    archivos = expositor.archivos.all()
    return render(request, "expositores/gestionar_archivos.html", {
        "expositor": expositor,
        "form": form,
        "archivos": archivos,
        "permisos": permisos,
    })

@require_POST
@permiso_o_superadmin_requerido('archivos_conferencista', 'editar')
def editar_archivo_expositor(request, id_archivo):
    archivo = get_object_or_404(ArchivoExpositor, id=id_archivo)
    nuevo_titulo = request.POST.get("titulo")
    if nuevo_titulo:
        archivo.titulo = nuevo_titulo
        archivo.save()
        messages.success(request, "Título del archivo actualizado correctamente.")
    else:
        messages.error(request, "El título no puede estar vacío.")
    return redirect('gestionar_archivos_expositor', idExpositor=archivo.expositor.idExpositor)

@require_POST
def eliminar_archivo_expositor(request, id_archivo):
    archivo = get_object_or_404(ArchivoExpositor, id=id_archivo)
    expositor_id = archivo.expositor.idExpositor
    archivo.archivo.delete(save=False)
    archivo.delete()
    messages.success(request, "Archivo eliminado correctamente.")
    return redirect('gestionar_archivos_expositor', idExpositor=expositor_id)
