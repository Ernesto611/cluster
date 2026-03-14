from django.contrib.auth.decorators import login_required
from .models import Evento, RegistroEvento, ArchivoEvento, CategoriaEvento, SubcategoriaEvento
from usuarios.models import DireccionGuardada
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .forms import EventoForm, ArchivoEventoForm, CategoriaEstiloForm
import os
from django.http import JsonResponse
from django.db.models import Q
from .decorators import role_required
from django.db.models import Q
from datetime import datetime
from django.utils.timezone import make_aware
from django.views.decorators.http import require_POST
from utils.permisos import (
    permiso_o_superadmin_requerido,
    permiso_listado,
    permisos_de_usuario,
    tiene_permiso_en_alguna_categoria,
    get_eventos_por_categoria
)
import base64, time
from django.core.files.base import ContentFile
from django.urls import reverse
from usuarios.models import PermisoPersonalizado

@login_required
@permiso_listado('eventos')
def listado(request):
    usuario = request.user
    permisos = permisos_de_usuario(usuario, 'eventos')
    permisos_archivos = permisos_de_usuario(usuario, 'archivos_evento')
    q = request.GET.get("q")
    fecha = request.GET.get("fecha")

    eventos = get_eventos_por_categoria(usuario, 'eventos')

    if q:
        eventos = eventos.filter(
            Q(aNombre__icontains=q) |
            Q(dCalle__icontains=q) |
            Q(dColonia__icontains=q) |
            Q(dCiudad__icontains=q) |
            Q(dEstado__icontains=q)
        )

    if fecha:
        try:
            fecha_obj = make_aware(datetime.strptime(fecha, "%Y-%m-%d"))
            eventos = eventos.filter(
                fFechaInicio__date__lte=fecha_obj.date(),
                fFechaFin__date__gte=fecha_obj.date()
            )
        except ValueError:
            pass

    eventos = eventos.order_by('-fFechaInicio')

    return render(request, 'eventos/listado.html', {
        'eventos': eventos,
        'q': q,
        'fecha': fecha,
        'permisos': permisos,
        'permisos_archivos': permisos_archivos,
    })

@login_required
@permiso_o_superadmin_requerido('eventos', 'agregar')
def agregar(request):
    if request.method == 'POST':
        form = EventoForm(request.POST, request.FILES)
        if form.is_valid():
            evento = form.save(commit=False)
            evento.organizador = request.user
            evento.save()
            if request.POST.get("guardar_direccion"):
                existe = DireccionGuardada.objects.filter(
                    usuario=request.user,
                    dCalle=evento.dCalle,
                    dNumero=evento.dNumero,
                    dColonia=evento.dColonia,
                    dCiudad=evento.dCiudad,
                    dEstado=evento.dEstado,
                    dCP=evento.dCP,
                ).exists()

                if not existe:
                    DireccionGuardada.objects.create(
                        usuario=request.user,
                        dCalle=evento.dCalle,
                        dNumero=evento.dNumero,
                        dColonia=evento.dColonia,
                        dCiudad=evento.dCiudad,
                        dEstado=evento.dEstado,
                        dCP=evento.dCP,
                        dLatitud=evento.dLatitud,
                        dLongitud=evento.dLongitud,
                        lPrivada=bool(request.POST.get("direccion_privada")),
                    )
            messages.success(request, 'El evento se creó correctamente.')
            return redirect('listado_eventos')
        else:
            print(f"Errores en el formulario: {form.errors}")
            messages.error(request, 'Hubo un error al crear el evento. Revisa los campos.')
    else:
        form = EventoForm()

    direcciones_disponibles = DireccionGuardada.objects.filter(
        Q(usuario=request.user) | Q(lPrivada=False)
    )

    return render(request, 'eventos/agregar.html', {'form': form,
    'direcciones_guardadas': direcciones_disponibles,})

@login_required
@permiso_listado('eventos')
def detalles(request, idEvento):
    evento = get_object_or_404(Evento, idEvento=idEvento)
    return render(request, 'eventos/detalles.html', {'evento': evento})

@login_required
@permiso_o_superadmin_requerido('eventos', 'editar')
def editar(request, idEvento):
    evento = get_object_or_404(Evento, idEvento=idEvento)

    if request.method == 'POST':
        form = EventoForm(request.POST, request.FILES, instance=evento)
        if form.is_valid():
            form.save()
            if request.POST.get("guardar_direccion"):
                existe = DireccionGuardada.objects.filter(
                    usuario=request.user,
                    dCalle=evento.dCalle,
                    dNumero=evento.dNumero,
                    dColonia=evento.dColonia,
                    dCiudad=evento.dCiudad,
                    dEstado=evento.dEstado,
                    dCP=evento.dCP,
                ).exists()

                if not existe:
                    DireccionGuardada.objects.create(
                        usuario=request.user,
                        dCalle=evento.dCalle,
                        dNumero=evento.dNumero,
                        dColonia=evento.dColonia,
                        dCiudad=evento.dCiudad,
                        dEstado=evento.dEstado,
                        dCP=evento.dCP,
                        dLatitud=evento.dLatitud,
                        dLongitud=evento.dLongitud,
                        lPrivada=bool(request.POST.get("direccion_privada")),
                    )
            messages.success(request, 'El evento se actualizó correctamente.')
            return redirect('listado_eventos')
        else:
            messages.error(request, 'Hubo un error al actualizar el evento. Revisa los campos.')
    else:
        form = EventoForm(instance=evento)
        if form.initial.get('dLatitud'):
            form.initial['dLatitud'] = str(form.initial['dLatitud']).replace(',', '.')
        if form.initial.get('dLongitud'):
            form.initial['dLongitud'] = str(form.initial['dLongitud']).replace(',', '.')

    direcciones_disponibles = DireccionGuardada.objects.filter(
        Q(usuario=request.user) | Q(lPrivada=False)
    )

    return render(request, 'eventos/editar.html', {'form': form, 'evento': evento,
    'direcciones_guardadas': direcciones_disponibles,})

@login_required
@role_required(["super_administrador"])
def eliminar(request, idEvento):
    evento = get_object_or_404(Evento, idEvento=idEvento)
    if request.method == 'POST':
        if evento.aImagen and os.path.isfile(evento.aImagen.path):
            os.remove(evento.aImagen.path)
        evento.delete()
        messages.success(request, 'El evento se eliminó correctamente.')
        return redirect('listado_eventos')
    return redirect('detalle_evento', idEvento=idEvento)

@login_required
@permiso_o_superadmin_requerido('eventos', 'desactivar')
def alternar_estado(request, idEvento):
    evento = get_object_or_404(Evento, idEvento=idEvento)
    if request.method == 'POST':
        evento.lActivo = not evento.lActivo
        evento.save()
        if evento.lActivo:
            messages.success(request, 'El evento se activó correctamente.')
        else:
            messages.success(request, 'El evento se desactivó correctamente.')
    return redirect('listado_eventos')

@login_required
@permiso_listado('registros_eventos')
def listar_registros_eventos(request):
    usuario = request.user
    registros = RegistroEvento.objects.select_related('usuario', 'evento')
    eventos_visibles = get_eventos_por_categoria(usuario, 'registros_eventos')

    registros = registros.filter(evento__in=eventos_visibles)

    q = request.GET.get('q')
    evento_id = request.GET.get('evento')

    if q:
        registros = registros.filter(
            Q(usuario__aNombre__icontains=q) | Q(usuario__aApellido__icontains=q) | Q(usuario__email__icontains=q)
        )
    if evento_id:
        registros = registros.filter(evento_id=evento_id)

    eventos = eventos_visibles.distinct()

    return render(request, 'eventos/registro_eventos.html', {
        'registros': registros,
        'eventos': eventos,
        'q': q,
        'evento_id': evento_id
    })

@login_required
@permiso_listado('archivos_evento')
def gestionar_archivos_evento(request, idEvento):
    evento = get_object_or_404(Evento, idEvento=idEvento)
    usuario = request.user
    permisos = permisos_de_usuario(usuario, 'archivos_evento')

    if request.method == "POST":
        form = ArchivoEventoForm(request.POST, request.FILES)
        if form.is_valid():
            archivo = form.save(commit=False)
            archivo.evento = evento
            archivo.save()
            messages.success(request, "Archivo subido correctamente.")
            return redirect('gestionar_archivos_evento', idEvento=evento.idEvento)
        else:
            messages.error(request, "Hubo un error al subir el archivo.")
    else:
        form = ArchivoEventoForm()

    archivos = evento.archivos.all()
    return render(request, "eventos/gestionar_archivos.html", {
        "evento": evento,
        "form": form,
        "archivos": archivos,
        'permisos': permisos,
    })

@require_POST
@permiso_o_superadmin_requerido('archivos_evento', 'editar')
def editar_archivo_evento(request, id_archivo):
    archivo = get_object_or_404(ArchivoEvento, id=id_archivo)
    nuevo_titulo = request.POST.get("titulo")
    if nuevo_titulo:
        archivo.titulo = nuevo_titulo
        archivo.save()
        messages.success(request, "Título del archivo actualizado correctamente.")
    else:
        messages.error(request, "El título no puede estar vacío.")
    return redirect('gestionar_archivos_evento', idEvento=archivo.evento.idEvento)

@login_required
@permiso_o_superadmin_requerido('archivos_evento', 'desactivar')
def alternar_estado_archivo(request, id):
    archivo = get_object_or_404(Archivo, id=id)
    if request.method == 'POST':
        archivo.lActivo = not archivo.lActivo
        archivo.save()
        if archivo.lActivo:
            messages.success(request, 'El archivo se activó correctamente.')
        else:
            messages.success(request, 'El archivo se desactivó correctamente.')

    return redirect('gestionar_archivos_evento', idEvento=archivo.evento.idEvento)

@require_POST
@permiso_o_superadmin_requerido('archivos_evento', 'borrar')
def eliminar_archivo_evento(request, id_archivo):
    archivo = get_object_or_404(ArchivoEvento, id=id_archivo)
    evento_id = archivo.evento.idEvento
    archivo.archivo.delete(save=False)
    archivo.delete()
    messages.success(request, "Archivo eliminado correctamente.")
    return redirect('gestionar_archivos_evento', idEvento=evento_id)

@login_required
@permiso_listado('categorias_eventos')
def listado_categorias(request):
    usuario = request.user
    permisos = permisos_de_usuario(usuario, 'categorias_eventos')
    q = request.GET.get("q")
    categorias_eventos = CategoriaEvento.objects.all()

    if q:
        categorias_eventos = categorias_eventos.filter(aNombre__icontains=q)

    categorias_eventos = categorias_eventos.order_by('aNombre')

    return render(request, 'eventos/listado_categorias.html', {
        'categorias_eventos': categorias_eventos,
        'q': q,
        'permisos': permisos,
    })

@login_required
@permiso_o_superadmin_requerido('categorias_eventos', 'agregar')
def agregar_categoria_evento(request):
    if request.method == 'POST':
        nombre = request.POST.get('aNombre', '').strip()
        if nombre:
            if not CategoriaEvento.objects.filter(aNombre=nombre).exists():
                CategoriaEvento.objects.create(aNombre=nombre, lActivo=True)
                messages.success(request, 'La categoria de evento se agregó correctamente.')
            else:
                messages.error(request, 'Ya existe un categoria de evento con este nombre.')
        else:
            messages.error(request, 'El nombre no puede estar vacío.')
    return redirect('listado_categorias_eventos')

@login_required
@permiso_o_superadmin_requerido('categorias_eventos', 'desactivar')
def alternar_estado_categoria_evento(request, idCategoria):
    categoria = get_object_or_404(CategoriaEvento, idCategoria=idCategoria)
    if request.method == 'POST':
        categoria.lActivo = not categoria.lActivo
        categoria.save()
        if categoria.lActivo:
            messages.success(request, 'La categoria de evento se activó correctamente.')
        else:
            messages.success(request, 'La categoria de evento se desactivó correctamente.')
    return redirect('listado_categorias_eventos')

@login_required
@permiso_o_superadmin_requerido('categorias_eventos', 'editar')
def editar_categoria_evento(request, idCategoria):
    categoria = get_object_or_404(CategoriaEvento, idCategoria=idCategoria)
    if request.method == 'POST':
        nombre = request.POST.get('aNombre', '').strip()
        if nombre:
            if CategoriaEvento.objects.exclude(idCategoria=idCategoria).filter(aNombre=nombre).exists():
                messages.error(request, 'Ya existe un categoria de evento con este nombre.')
            else:
                categoria.aNombre = nombre
                categoria.save()
                messages.success(request, 'La categoria de evento se actualizó correctamente.')
        else:
            messages.error(request, 'El nombre no puede estar vacío.')
    return redirect('listado_categorias_eventos')

def _categorias_con_permiso_editar_estilos(usuario):

    if getattr(usuario, "tipo_usuario", "") == "super_administrador":
        return CategoriaEvento.objects.all().order_by("aNombre")

    ids = (PermisoPersonalizado.objects
           .filter(usuario=usuario, categoria="categorias_eventos", accion="editar_estilos")
           .values_list("valor", flat=True))
    ids_limpios = []
    for v in ids:
        try:
            ids_limpios.append(int(v))
        except (TypeError, ValueError):
            continue

    return CategoriaEvento.objects.filter(idCategoria__in=ids_limpios).order_by("aNombre")

@login_required
@permiso_o_superadmin_requerido('categorias_eventos', 'editar_estilos')
def configurar_estilos_categoria(request, categoria_id: int):

    categorias_permitidas = _categorias_con_permiso_editar_estilos(request.user)
    if getattr(request.user, "tipo_usuario", "") == "super_administrador":
        categoria = get_object_or_404(CategoriaEvento, idCategoria=categoria_id)
    else:
        categoria = get_object_or_404(categorias_permitidas, idCategoria=categoria_id)

    if request.method == "POST":
        form = CategoriaEstiloForm(request.POST, request.FILES, instance=categoria)

        logo_cropped = request.POST.get("logo_cropped")
        if logo_cropped and logo_cropped.startswith("data:image/"):
            try:
                head, b64data = logo_cropped.split(";base64,")
                ext = head.split("/")[-1].lower()
                if ext not in ("png", "jpeg", "jpg", "webp"):
                    ext = "png"
                data = base64.b64decode(b64data)
                fname = f"logo_categoria_{categoria.idCategoria}_{int(time.time())}.{ 'jpg' if ext=='jpeg' else ext}"
                categoria.logo.save(fname, ContentFile(data), save=False)
            except Exception:
                messages.error(request, "No se pudo procesar el logo recortado. Intenta de nuevo.")
                return render(request, "eventos/configurar_estilos.html", {
                    "form": form, "categoria": categoria,
                })

        if form.is_valid():
            form.save()
            messages.success(request, "Estilos actualizados correctamente.")
            return redirect("configurar_estilos_categoria", categoria_id=categoria.idCategoria)

        return render(request, "eventos/configurar_estilos.html", {
            "form": form, "categoria": categoria,
        })

    form = CategoriaEstiloForm(instance=categoria)
    return render(request, "eventos/configurar_estilos.html", {
        "form": form, "categoria": categoria,
    })

@login_required
@permiso_listado('subcategorias_eventos')
def listado_subcategorias(request):
    usuario = request.user
    permisos = permisos_de_usuario(usuario, 'subcategorias_eventos')
    q = request.GET.get("q")
    subcategorias = SubcategoriaEvento.objects.select_related('categoria').all()
    categorias = CategoriaEvento.objects.filter(lActivo=True)
    categoria_id = request.GET.get("categoria")
    if categoria_id:
        subcategorias = subcategorias.filter(categoria__idCategoria=categoria_id)

    if q:
        subcategorias = subcategorias.filter(
            Q(aNombre__icontains=q) | Q(categoria__aNombre__icontains=q)
        )

    subcategorias = subcategorias.order_by('aNombre')

    return render(request, 'eventos/listado_subcategorias.html', {
        'subcategorias': subcategorias,
        'q': q,
        'permisos': permisos,
        'categorias': categorias,
        'categoria_id': categoria_id,
    })

@login_required
@permiso_o_superadmin_requerido('subcategorias_eventos', 'agregar')
def agregar_subcategoria_evento(request):
    if request.method == 'POST':
        nombre = request.POST.get('aNombre', '').strip()
        id_categoria = request.POST.get('categoria')
        if nombre and id_categoria:
            if not SubcategoriaEvento.objects.filter(aNombre=nombre).exists():
                categoria = get_object_or_404(CategoriaEvento, idCategoria=id_categoria)
                SubcategoriaEvento.objects.create(aNombre=nombre, categoria=categoria, lActivo=True)
                messages.success(request, 'La subcategoría de evento se agregó correctamente.')
            else:
                messages.error(request, 'Ya existe una subcategoría con ese nombre.')
        else:
            messages.error(request, 'Todos los campos son obligatorios.')
    return redirect('listado_subcategorias_eventos')

@login_required
@permiso_o_superadmin_requerido('subcategorias_eventos', 'editar')
def editar_subcategoria_evento(request, id):
    subcategoria = get_object_or_404(SubcategoriaEvento, id=id)
    if request.method == 'POST':
        nombre = request.POST.get('aNombre', '').strip()
        id_categoria = request.POST.get('categoria')
        if nombre and id_categoria:
            if SubcategoriaEvento.objects.exclude(id=subcategoria.id).filter(aNombre=nombre).exists():
                messages.error(request, 'Ya existe una subcategoría con ese nombre.')
            else:
                subcategoria.aNombre = nombre
                subcategoria.categoria = get_object_or_404(CategoriaEvento, idCategoria=id_categoria)
                subcategoria.save()
                messages.success(request, 'La subcategoría se actualizó correctamente.')
        else:
            messages.error(request, 'Todos los campos son obligatorios.')
    return redirect('listado_subcategorias_eventos')

@login_required
@permiso_o_superadmin_requerido('subcategorias_eventos', 'desactivar')
def alternar_estado_subcategoria_evento(request, id):
    subcategoria = get_object_or_404(SubcategoriaEvento, id=id)
    if request.method == 'POST':
        subcategoria.lActivo = not subcategoria.lActivo
        subcategoria.save()
        estado = "activó" if subcategoria.lActivo else "desactivó"
        messages.success(request, f'La subcategoría se {estado} correctamente.')
    return redirect('listado_subcategorias_eventos')

def obtener_subcategorias_por_categoria(request):
    id_categoria = request.GET.get("id_categoria")
    subcategorias = []
    if id_categoria:
        subcategorias_qs = SubcategoriaEvento.objects.filter(categoria_id=id_categoria, lActivo=True).values('id', 'aNombre')
        subcategorias = list(subcategorias_qs)
    return JsonResponse({'subcategorias': subcategorias})
