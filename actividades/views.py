from datetime import datetime
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from usuarios.models import DireccionGuardada
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.timezone import make_aware
from .decorators import role_required
from .forms import ActividadForm
from .models import Actividad, TipoActividad, RegistroActividad, AcompañanteActividad
from eventos.models import Evento, RegistroEvento
from utils.permisos import (
    permiso_o_superadmin_requerido,
    permiso_listado,
    permisos_de_usuario,
    tiene_permiso_en_alguna_categoria,
    get_eventos_por_categoria,
    get_actividades_por_categoria,
    get_alcance_categoria
)

@login_required
@permiso_listado('tipos_actividades')
def listado_tipos(request):
    usuario = request.user
    permisos = permisos_de_usuario(usuario, 'tipos_actividades')

    q = request.GET.get("q")
    tipos_actividades = TipoActividad.objects.all()

    if q:
        tipos_actividades = tipos_actividades.filter(aNombre__icontains=q)

    tipos_actividades = tipos_actividades.order_by('aNombre')

    return render(request, 'actividades/listado_tipos.html', {
        'tipos_actividades': tipos_actividades,
        'q': q,
        'permisos': permisos,
    })

@login_required
@permiso_listado('actividades')
def listado(request):
    usuario = request.user
    permisos = permisos_de_usuario(usuario, 'actividades')
    actividades = get_actividades_por_categoria(usuario, 'actividades')

    q = request.GET.get("q")
    evento_id = request.GET.get("evento")
    fecha = request.GET.get("fecha")

    if q:
        actividades = actividades.filter(
            Q(aNombre__icontains=q) |
            Q(nCapacidad__icontains=q) |
            Q(nCosto__icontains=q)
        )

    if evento_id:
        actividades = actividades.filter(idEvento__idEvento=evento_id)

    if fecha:
        try:
            fecha_obj = make_aware(datetime.strptime(fecha, "%Y-%m-%d"))
            actividades = actividades.filter(
                fFechaHoraInicio__date__lte=fecha_obj.date(),
                fFechaHoraFin__date__gte=fecha_obj.date()
            )
        except ValueError:
            pass

    actividades = actividades.order_by('fFechaHoraInicio')

    eventos_ids = actividades.values_list('idEvento__idEvento', flat=True).distinct()
    eventos = Evento.objects.filter(idEvento__in=eventos_ids)

    return render(request, 'actividades/listado.html', {
        'actividades': actividades,
        'eventos': eventos,
        'q': q,
        'evento_id': evento_id,
        'fecha': fecha,
        'permisos': permisos,
    })

@login_required
@permiso_o_superadmin_requerido('actividades', 'agregar')
def agregar_actividad(request):
    usuario = request.user
    actividades = get_actividades_por_categoria(usuario, 'actividades')
    alcance = get_alcance_categoria(usuario, 'actividades')

    if alcance == 'actividad':
        eventos_ids = actividades.values_list('idEvento__idEvento', flat=True).distinct()
        eventos_permitidos = Evento.objects.filter(idEvento__in=eventos_ids)
    else:
        eventos_permitidos = get_eventos_por_categoria(usuario, 'actividades')

    if request.method == 'POST':
        form = ActividadForm(request.POST)
        form.fields['idEvento'].queryset = eventos_permitidos

        if form.is_valid():
            actividad = form.save(commit=False)
            actividad.nLugaresDisponibles = actividad.nCapacidad
            actividad.save()
            if request.POST.get("guardar_direccion"):
                existe = DireccionGuardada.objects.filter(
                    usuario=request.user,
                    dCalle=actividad.dCalle,
                    dNumero=actividad.dNumero,
                    dColonia=actividad.dColonia,
                    dCiudad=actividad.dCiudad,
                    dEstado=actividad.dEstado,
                    dCP=actividad.dCP,
                ).exists()

                if not existe:
                    DireccionGuardada.objects.create(
                        usuario=request.user,
                        dCalle=actividad.dCalle,
                        dNumero=actividad.dNumero,
                        dColonia=actividad.dColonia,
                        dCiudad=actividad.dCiudad,
                        dEstado=actividad.dEstado,
                        dCP=actividad.dCP,
                        dLatitud=actividad.dLatitud,
                        dLongitud=actividad.dLongitud,
                        lPrivada=bool(request.POST.get("direccion_privada")),
                    )

            messages.success(request, 'La actividad se creó correctamente.')
            return redirect('listado_actividades')
        else:
            messages.error(request, 'Hubo un error al crear la actividad. Por favor, verifica los campos.')
    else:
        form = ActividadForm()
        form.fields['idEvento'].queryset = eventos_permitidos

    direcciones_disponibles = DireccionGuardada.objects.filter(
        Q(usuario=request.user) | Q(lPrivada=False)
    )

    return render(request, 'actividades/agregar.html', {'form': form,
    'direcciones_guardadas': direcciones_disponibles,})

@login_required
@permiso_listado('actividades')
def detalles_actividad(request, idActividad):
    actividad = get_object_or_404(Actividad, idActividad=idActividad)
    return render(request, 'actividades/detalles_actividad.html', {'actividad': actividad})

@login_required
@permiso_o_superadmin_requerido('actividades', 'editar')
def editar_actividad(request, idActividad):
    actividad = get_object_or_404(Actividad, idActividad=idActividad)
    usuario = request.user
    actividades = get_actividades_por_categoria(usuario, 'actividades')
    alcance = get_alcance_categoria(usuario, 'actividades')

    if alcance == 'actividad':
        eventos_ids = actividades.values_list('idEvento__idEvento', flat=True).distinct()
        eventos_permitidos = Evento.objects.filter(idEvento__in=eventos_ids)
    else:
        eventos_permitidos = get_eventos_por_categoria(usuario, 'actividades')

    if actividad.idEvento not in eventos_permitidos:
        messages.error(request, "No tienes permisos para editar esta actividad.")
        return redirect("listado_actividades")

    if request.method == 'POST':
        form = ActividadForm(request.POST, instance=actividad)
        form.fields['idEvento'].queryset = eventos_permitidos

        if form.is_valid():
            actividad = form.save()
            if request.POST.get("guardar_direccion"):
                existe = DireccionGuardada.objects.filter(
                    usuario=request.user,
                    dCalle=actividad.dCalle,
                    dNumero=actividad.dNumero,
                    dColonia=actividad.dColonia,
                    dCiudad=actividad.dCiudad,
                    dEstado=actividad.dEstado,
                    dCP=actividad.dCP,
                ).exists()

                if not existe:
                    DireccionGuardada.objects.create(
                        usuario=request.user,
                        dCalle=actividad.dCalle,
                        dNumero=actividad.dNumero,
                        dColonia=actividad.dColonia,
                        dCiudad=actividad.dCiudad,
                        dEstado=actividad.dEstado,
                        dCP=actividad.dCP,
                        dLatitud=actividad.dLatitud,
                        dLongitud=actividad.dLongitud,
                        lPrivada=bool(request.POST.get("direccion_privada")),
                    )
            messages.success(request, 'La actividad se actualizó correctamente.')
            return redirect('listado_actividades')
        else:
            messages.error(request, 'Hubo un error al actualizar la actividad. Por favor, verifica los campos.')
    else:
        form = ActividadForm(instance=actividad)
        form.fields['idEvento'].queryset = eventos_permitidos

    direcciones_disponibles = DireccionGuardada.objects.filter(
        Q(usuario=request.user) | Q(lPrivada=False)
    )

    return render(request, 'actividades/editar_actividad.html', {
        'form': form,
        'actividad': actividad,
        'direcciones_guardadas': direcciones_disponibles,
    })

@login_required
@permiso_o_superadmin_requerido('actividades', 'desactivar')
def alternar_estado_actividad(request, idActividad):
    actividad = get_object_or_404(Actividad, idActividad=idActividad)
    if request.method == 'POST':
        actividad.lActivo = not actividad.lActivo
        actividad.save()
        if actividad.lActivo:
            messages.success(request, 'La actividad se activó correctamente.')
        else:
            messages.success(request, 'La actividad se desactivó correctamente.')
    return redirect('listado_actividades')

@login_required
@role_required(["super_administrador"])
def eliminar_actividad(request, idActividad):
    actividad = get_object_or_404(Actividad, idActividad=idActividad)
    if request.method == 'POST':
        actividad.delete()
        messages.success(request, 'La actividad se eliminó correctamente.')
    return redirect('listado_actividades')

@login_required
@permiso_listado('actividades')
def obtener_actividades_por_evento(request):
    usuario = request.user
    evento_id = request.GET.get('evento_id')
    actividades_permitidas = get_actividades_por_categoria(usuario, 'actividades')

    actividades = actividades_permitidas.filter(
        idEvento=evento_id,
        lActivo=True
    ).values('idActividad', 'aNombre')

    return JsonResponse(list(actividades), safe=False)

@login_required
@permiso_listado('registros_actividades')
def listar_registros_actividades(request):
    usuario = request.user
    registros = RegistroActividad.objects.select_related('usuario', 'actividad', 'actividad__idEvento')
    actividades_visibles = get_actividades_por_categoria(usuario, 'registros_actividades')
    alcance = get_alcance_categoria(usuario, 'registros_actividades')

    if alcance == 'actividad':
        eventos_ids = actividades_visibles.values_list('idEvento__idEvento', flat=True).distinct()
        eventos_visibles = Evento.objects.filter(idEvento__in=eventos_ids)
    else:
        eventos_visibles = get_eventos_por_categoria(usuario, 'registros_actividades')

    registros = registros.filter(actividad__in=actividades_visibles)

    q = request.GET.get('q')
    evento_id = request.GET.get('evento')
    actividad_id = request.GET.get('actividad')

    if q:
        registros = registros.filter(Q(usuario__aNombre__icontains=q) | Q(usuario__aApellido__icontains=q) | Q(usuario__email__icontains=q))
    if evento_id:
        actividades_filtradas = actividades_visibles.filter(idEvento_id=evento_id)
        registros = registros.filter(actividad__in=actividades_filtradas)
    if actividad_id:
        registros = registros.filter(actividad_id=actividad_id)

    return render(request, 'actividades/registro_actividades.html', {
        'registros': registros,
        'eventos': eventos_visibles,
        'actividades': actividades_visibles,
        'q': q,
        'evento_id': evento_id,
        'actividad_id': actividad_id
    })

@login_required
@permiso_o_superadmin_requerido('tipos_actividades', 'agregar')
def agregar_tipo_actividad(request):
    if request.method == 'POST':
        nombre = request.POST.get('aNombre', '').strip()
        if nombre:
            if not TipoActividad.objects.filter(aNombre=nombre).exists():
                TipoActividad.objects.create(aNombre=nombre, lActivo=True)
                messages.success(request, 'El tipo de actividad se agregó correctamente.')
            else:
                messages.error(request, 'Ya existe un tipo de actividad con este nombre.')
        else:
            messages.error(request, 'El nombre no puede estar vacío.')
    return redirect('listado_tipos_actividades')

@login_required
@permiso_o_superadmin_requerido('tipos_actividades', 'desactivar')
def alternar_estado_tipo_actividad(request, idTipo):
    tipo = get_object_or_404(TipoActividad, idTipo=idTipo)
    if request.method == 'POST':
        tipo.lActivo = not tipo.lActivo
        tipo.save()
        if tipo.lActivo:
            messages.success(request, 'El tipo de actividad se activó correctamente.')
        else:
            messages.success(request, 'El tipo de actividad se desactivó correctamente.')
    return redirect('listado_tipos_actividades')

@login_required
@permiso_o_superadmin_requerido('tipos_actividades', 'editar')
def editar_tipo_actividad(request, idTipo):
    tipo = get_object_or_404(TipoActividad, idTipo=idTipo)
    if request.method == 'POST':
        nombre = request.POST.get('aNombre', '').strip()
        if nombre:
            if TipoActividad.objects.exclude(idTipo=idTipo).filter(aNombre=nombre).exists():
                messages.error(request, 'Ya existe un tipo de actividad con este nombre.')
            else:
                tipo.aNombre = nombre
                tipo.save()
                messages.success(request, 'El tipo de actividad se actualizó correctamente.')
        else:
            messages.error(request, 'El nombre no puede estar vacío.')
    return redirect('listado_tipos_actividades')

@login_required
@role_required(["super_administrador"])
def eliminar_tipo_actividad(request, idTipo):
    tipo = get_object_or_404(TipoActividad, idTipo=idTipo)
    if request.method == 'POST':
        tipo.delete()
        messages.success(request, 'El tipo de actividad se eliminó correctamente.')
    return redirect('listado_tipos_actividades')
