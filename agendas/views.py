import json
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from .decorators import role_required
from .forms import AgendaForm, AgendaActividadesForm
from .models import Agenda, AgendaActividades
from actividades.models import Actividad
from django.urls import reverse
from eventos.models import Evento
from utils.permisos import (
    permiso_o_superadmin_requerido,
    permiso_listado,
    permisos_de_usuario,
    tiene_permiso_en_alguna_categoria,
    get_eventos_por_categoria,
    get_actividades_por_categoria
)

@login_required
@permiso_listado('agendas')
def listado(request):
    usuario = request.user
    permisos = permisos_de_usuario(usuario, 'agendas')
    q = request.GET.get("q")
    evento_id = request.GET.get("evento")
    eventos = get_eventos_por_categoria(usuario, 'agendas')
    eventos_ids = eventos.values_list('idEvento', flat=True).distinct()
    agendas = Agenda.objects.filter(idEvento__idEvento__in=eventos_ids)

    if q:
        agendas = agendas.filter(aNombre__icontains=q)

    if evento_id:
        agendas = agendas.filter(idEvento__idEvento=evento_id)

    agendas = agendas.order_by('-idAgenda')

    return render(request, 'agendas/listado.html', {
        'agendas': agendas,
        'eventos': eventos,
        'q': q,
        'evento_id': evento_id,
        'permisos': permisos,
    })

@login_required
@permiso_o_superadmin_requerido('agendas', 'desactivar')
def alternar_estado_agenda(request, idAgenda):
    agenda = get_object_or_404(Agenda, idAgenda=idAgenda)
    if request.method == 'POST':
        agenda.lActivo = not agenda.lActivo
        agenda.save()
        if agenda.lActivo:
            messages.success(request, 'La agenda se activó correctamente.')
        else:
            messages.success(request, 'La agenda se desactivó correctamente.')
    return redirect('listado_agendas')

@login_required
@role_required(["super_administrador"])
def eliminar(request, idAgenda):
    agenda = get_object_or_404(Agenda, idAgenda=idAgenda)
    if request.method == 'POST':
        agenda.delete()
        messages.success(request, "La agenda ha sido eliminada correctamente.")
        return redirect('listado_agendas')
    return render(request, 'agendas/listado.html', {'agenda': agenda})

@login_required
@permiso_o_superadmin_requerido('agendas', 'agregar')
def agregar(request):
    usuario = request.user
    eventos_permitidos = get_eventos_por_categoria(usuario, 'agendas')

    if request.method == 'POST':
        form = AgendaForm(request.POST)
        form.fields['idEvento'].queryset = eventos_permitidos

        if form.is_valid():
            agenda = form.save(commit=False)
            agenda.idUsuario = usuario
            agenda.save()

            actividades_ids = request.POST.get('actividades', '[]')
            try:
                actividades_ids = json.loads(actividades_ids)
                for actividad_id in actividades_ids:
                    actividad = Actividad.objects.get(idActividad=actividad_id)
                    AgendaActividades.objects.create(idAgenda=agenda, idActividad=actividad)

                messages.success(request, 'Agenda creada exitosamente')
                return JsonResponse({'success': True, 'redirect_url': reverse('listado_agendas')})
            except Exception as e:
                return JsonResponse({'success': False, 'error': str(e)}, status=400)

        return JsonResponse({'success': False, 'error': form.errors}, status=400)

    form = AgendaForm()
    form.fields['idEvento'].queryset = eventos_permitidos

    primer_evento = eventos_permitidos.first()
    actividades = []

    return render(request, 'agendas/agregar.html', {
        'form': form,
        'actividades': actividades
    })

def obtener_actividades_por_evento(request):
    evento_id = request.GET.get('evento_id')
    actividades = Actividad.objects.filter(idEvento=evento_id, lActivo=True).values(
        'idActividad', 'aNombre', 'idTipo__aNombre', 'fFechaHoraInicio', 'fFechaHoraFin'
    )
    return JsonResponse(list(actividades), safe=False)

def obtener_actividades_json(request):
    actividades = Actividad.objects.filter(lActivo=True)
    data = [
        {
            'id': actividad.idActividad,
            'title': actividad.aNombre,
            'start': actividad.fFechaHoraInicio.isoformat(),
            'end': actividad.fFechaHoraFin.isoformat(),
            'backgroundColor': '#0ab39c',
        } for actividad in actividades
    ]
    return JsonResponse(data, safe=False)

@login_required
@permiso_o_superadmin_requerido('agendas', 'editar')
def editar(request, idAgenda):
    usuario = request.user
    agenda = get_object_or_404(Agenda, idAgenda=idAgenda)
    eventos_permitidos = get_eventos_por_categoria(usuario, 'agendas')

    actividades_asignadas = agenda.agenda_actividades.values_list('idActividad', flat=True)
    actividades = Actividad.objects.filter(idEvento=agenda.idEvento, lActivo=True)

    if request.method == 'POST':
        form = AgendaForm(request.POST, instance=agenda)
        form.fields['idEvento'].queryset = eventos_permitidos

        actividades_json = request.POST.get('actividades', '[]')
        try:
            actividades_ids = json.loads(actividades_json)
            actividades_ids = [int(id) for id in actividades_ids]
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Formato inválido de actividades'}, status=400)

        if form.is_valid():
            if not actividades_ids:
                return JsonResponse({'success': False, 'error': 'Debe seleccionar al menos una actividad'}, status=400)

            agenda = form.save()
            agenda.agenda_actividades.all().delete()

            actividades_seleccionadas = Actividad.objects.filter(idActividad__in=actividades_ids)
            for actividad in actividades_seleccionadas:
                AgendaActividades.objects.create(idAgenda=agenda, idActividad=actividad)
            messages.success(request, 'Agenda editada exitosamente')
            return JsonResponse({'success': True, 'redirect_url': reverse('listado_agendas')})
        else:
            return JsonResponse({'success': False, 'error': form.errors}, status=400)

    else:
        form = AgendaForm(instance=agenda)
        form.fields['idEvento'].queryset = eventos_permitidos

    return render(request, 'agendas/editar.html', {
        'form': form,
        'agenda': agenda,
        'actividades_asignadas': list(actividades_asignadas),
        'actividades': actividades
    })

@login_required
@permiso_listado('agendas')
def detalles(request, idAgenda):
    agenda = get_object_or_404(Agenda, idAgenda=idAgenda)
    actividades = agenda.agenda_actividades.all()
    return render(request, 'agendas/detalles.html', {'agenda': agenda, 'actividades': actividades})
