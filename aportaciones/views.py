from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from utils.permisos import (
    permiso_listado,
    permiso_o_superadmin_requerido,
    permisos_de_usuario,
    get_eventos_por_categoria,
)
from .models import Aportador, Aportacion
from eventos.models import Evento
from utils.fechas import ahora_mx

@login_required
@permiso_listado('aportadores')
def listado_aportadores(request):
    usuario = request.user
    permisos = permisos_de_usuario(usuario, 'aportadores')

    q = request.GET.get("q")
    aportadores = Aportador.objects.all()

    if q:
        aportadores = aportadores.filter(
            Q(aNombre__icontains=q) |
            Q(aEmail__icontains=q)
        )

    aportadores = aportadores.order_by('aNombre')

    return render(request, 'aportaciones/listado_aportadores.html', {
        'aportadores': aportadores,
        'q': q,
        'permisos': permisos,
    })

@login_required
@permiso_o_superadmin_requerido('aportadores', 'agregar')
def agregar_aportador(request):
    if request.method == 'POST':
        nombre = request.POST.get('aNombre', '').strip()
        email = request.POST.get('aEmail', '').strip()
        if nombre and email:
            if not Aportador.objects.filter(aEmail=email).exists():
                Aportador.objects.create(aNombre=nombre, aEmail=email, lActivo=True)
                messages.success(request, 'El aportador se agregó correctamente.')
            else:
                messages.error(request, 'Ya existe un aportador con este email.')
        else:
            messages.error(request, 'El nombre y el email son obligatorios.')
    return redirect('listado_aportadores')

@login_required
@permiso_o_superadmin_requerido('aportadores', 'editar')
def editar_aportador(request, idAportador):
    aportador = get_object_or_404(Aportador, idAportador=idAportador)
    if request.method == 'POST':
        nombre = request.POST.get('aNombre', '').strip()
        email = request.POST.get('aEmail', '').strip()
        if nombre and email:
            if not Aportador.objects.exclude(idAportador=idAportador).filter(aEmail=email).exists():
                aportador.aNombre = nombre
                aportador.aEmail = email
                aportador.save()
                messages.success(request, 'El aportador se actualizó correctamente.')
            else:
                messages.error(request, 'Ya existe un aportador con este email.')
        else:
            messages.error(request, 'El nombre y el email son obligatorios.')
    return redirect('listado_aportadores')

@login_required
@permiso_o_superadmin_requerido('aportadores', 'desactivar')
def alternar_estado_aportador(request, idAportador):
    aportador = get_object_or_404(Aportador, idAportador=idAportador)
    if request.method == 'POST':
        aportador.lActivo = not aportador.lActivo
        aportador.save()
        if aportador.lActivo:
            messages.success(request, 'El aportador se activó correctamente.')
        else:
            messages.success(request, 'El aportador se desactivó correctamente.')
    return redirect('listado_aportadores')

@login_required
@permiso_listado('aportaciones')
def listado_aportaciones(request):
    usuario = request.user
    permisos = permisos_de_usuario(usuario, 'aportaciones')
    eventos = get_eventos_por_categoria(usuario, 'aportaciones')
    eventos_ids = eventos.values_list('idEvento', flat=True).distinct()

    q = request.GET.get("q")
    aportaciones = Aportacion.objects.filter(idEvento__in=eventos_ids)

    if q:
        aportaciones = aportaciones.filter(
            Q(aNombre__icontains=q) |
            Q(aDescripcion__icontains=q) |
            Q(idAportador__aNombre__icontains=q)
        )

    aportaciones = aportaciones.order_by('-fCreacion')

    return render(request, 'aportaciones/listado_aportaciones.html', {
        'aportaciones': aportaciones,
        'q': q,
        'permisos': permisos,
    })

@login_required
@permiso_o_superadmin_requerido('aportaciones', 'agregar')
def agregar_aportacion(request):
    usuario = request.user
    eventos_disponibles = get_eventos_por_categoria(usuario, 'aportaciones')
    aportadores_activos = Aportador.objects.filter(lActivo=True)

    if request.method == 'POST':
        nombre = request.POST.get('aNombre', '').strip()
        descripcion = request.POST.get('aDescripcion', '').strip()
        id_evento = request.POST.get('idEvento')
        id_aportador = request.POST.get('idAportador')
        monto = request.POST.get('monto_pago')

        if nombre and descripcion and id_evento and id_aportador and monto:
            try:
                monto = float(monto)
                if monto <= 0:
                    messages.error(request, 'El monto debe ser mayor a 0.')
                    return render(request, 'aportaciones/agregar_aportacion.html', {
                        'eventos': eventos_disponibles,
                        'aportadores': aportadores_activos,
                    })

                evento = eventos_disponibles.get(idEvento=id_evento)
                aportador = aportadores_activos.get(idAportador=id_aportador)

                Aportacion.objects.create(
                    aNombre=nombre,
                    aDescripcion=descripcion,
                    idEvento=evento,
                    idAportador=aportador,
                    monto_pago=monto
                )
                messages.success(request, 'La aportación se agregó correctamente.')
                return redirect('listado_aportaciones')
            except ValueError:
                messages.error(request, 'El monto ingresado no es válido.')
            except (Evento.DoesNotExist, Aportador.DoesNotExist):
                messages.error(request, 'El evento o aportador seleccionado no es válido.')
        else:
            messages.error(request, 'Todos los campos son obligatorios.')

    return render(request, 'aportaciones/agregar_aportacion.html', {
        'eventos': eventos_disponibles,
        'aportadores': aportadores_activos,
    })

@login_required
@permiso_o_superadmin_requerido('aportaciones', 'editar')
def editar_aportacion(request, idAportacion):
    usuario = request.user
    eventos_disponibles = get_eventos_por_categoria(usuario, 'aportaciones')
    aportadores_activos = Aportador.objects.filter(lActivo=True)
    aportacion = get_object_or_404(Aportacion, idAportacion=idAportacion, idEvento__in=eventos_disponibles)

    if request.method == 'POST':
        nombre = request.POST.get('aNombre', '').strip()
        descripcion = request.POST.get('aDescripcion', '').strip()
        id_evento = request.POST.get('idEvento')
        id_aportador = request.POST.get('idAportador')
        monto = request.POST.get('monto_pago')

        if nombre and descripcion and id_evento and id_aportador and monto:
            try:
                monto = float(monto)
                if monto <= 0:
                    messages.error(request, 'El monto debe ser mayor a 0.')
                    return render(request, 'aportaciones/editar_aportacion.html', {
                        'aportacion': aportacion,
                        'eventos': eventos_disponibles,
                        'aportadores': aportadores_activos,
                    })

                evento = eventos_disponibles.get(idEvento=id_evento)
                aportador = aportadores_activos.get(idAportador=id_aportador)

                aportacion.aNombre = nombre
                aportacion.aDescripcion = descripcion
                aportacion.idEvento = evento
                aportacion.idAportador = aportador
                aportacion.monto_pago = monto
                aportacion.save()

                messages.success(request, 'La aportación se actualizó correctamente.')
                return redirect('listado_aportaciones')
            except ValueError:
                messages.error(request, 'El monto ingresado no es válido.')
            except (Evento.DoesNotExist, Aportador.DoesNotExist):
                messages.error(request, 'El evento o aportador seleccionado no es válido.')
        else:
            messages.error(request, 'Todos los campos son obligatorios.')

    return render(request, 'aportaciones/editar_aportacion.html', {
        'aportacion': aportacion,
        'eventos': eventos_disponibles,
        'aportadores': aportadores_activos,
    })

@login_required
@permiso_o_superadmin_requerido('aportaciones', 'editar')
def marcar_como_pagada(request, idAportacion):
    usuario = request.user
    eventos_disponibles = get_eventos_por_categoria(usuario, 'aportaciones')
    aportacion = get_object_or_404(Aportacion, idAportacion=idAportacion, idEvento__in=eventos_disponibles)

    if request.method == 'POST':
        if aportacion.eEstado == 'pendiente':
            aportacion.marcar_como_pagada()
            messages.success(request, 'La aportación se marcó como pagada correctamente.')
        else:
            messages.error(request, 'La aportación ya está marcada como pagada.')

    return redirect('listado_aportaciones')
