import random
import string
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from .decorators import role_required
from .forms import EntradaForm, CuponForm
from .models import Entrada, EntradaActividad, CompraEntrada, Cupon
from actividades.models import Actividad
from eventos.models import Evento
from web.views import enviar_correo_confirmacion
from utils.permisos import (
    permiso_o_superadmin_requerido,
    permiso_listado,
    permisos_de_usuario,
    tiene_permiso_en_alguna_categoria,
    get_eventos_por_categoria,
    get_actividades_por_categoria
)

@login_required
@permiso_listado('entradas')
def listado(request):
    usuario = request.user
    permisos = permisos_de_usuario(usuario, 'entradas')
    permisos_cupones = permisos_de_usuario(usuario, 'cupones_entrada')
    eventos = get_eventos_por_categoria(usuario, 'entradas')
    eventos_ids = eventos.values_list('idEvento', flat=True).distinct()
    entradas = Entrada.objects.filter(idEvento__idEvento__in=eventos_ids)
    q = request.GET.get("q")
    evento_id = request.GET.get("evento")

    if q:
        entradas = entradas.filter(
            Q(aNombre__icontains=q) |
            Q(nCosto__icontains=q) |
            Q(nCantidad__icontains=q)
        )

    if evento_id:
        entradas = entradas.filter(idEvento__idEvento=evento_id)

    entradas = entradas.order_by('-idEntrada')

    return render(request, 'entradas/listado.html', {
        'entradas': entradas,
        'eventos': eventos,
        'q': q,
        'evento_id': evento_id,
        'permisos': permisos,
        'permisos_cupones': permisos_cupones,
    })

@login_required
@permiso_o_superadmin_requerido('entradas', 'desactivar')
def alternar_estado_entrada(request, idEntrada):
    entrada = get_object_or_404(Entrada, idEntrada=idEntrada)
    if request.method == 'POST':
        entrada.lActivo = not entrada.lActivo
        entrada.save()
        if entrada.lActivo:
            messages.success(request, 'La entrada se activó correctamente.')
        else:
            messages.success(request, 'La entrada se desactivó correctamente.')
    return redirect('listado_entradas')

@login_required
@permiso_o_superadmin_requerido('entradas', 'agregar')
def agregar(request):
    usuario = request.user
    eventos_permitidos = get_eventos_por_categoria(usuario, 'entradas')

    if request.method == 'POST':
        form = EntradaForm(request.POST)
        form.fields['idEvento'].queryset = eventos_permitidos

        if form.is_valid():
            entrada = form.save()
            messages.success(request, 'La entrada y sus actividades se guardaron correctamente.')
            return redirect('listado_entradas')
        else:
            messages.error(request, 'Hubo un error al crear la entrada. Revisa los campos.')
    else:
        form = EntradaForm()
        form.fields['idEvento'].queryset = eventos_permitidos

    return render(request, 'entradas/agregar.html', {'form': form})

def obtener_actividades(request, evento_id):
    actividades = Actividad.objects.filter(idEvento=evento_id).values('idActividad', 'aNombre')
    return JsonResponse(list(actividades), safe=False)

@login_required
@permiso_o_superadmin_requerido('entradas', 'editar')
def editar_entrada(request, idEntrada):
    entrada = get_object_or_404(Entrada, idEntrada=idEntrada)
    usuario = request.user
    eventos_permitidos = get_eventos_por_categoria(usuario, 'entradas')

    if request.method == 'POST':
        form = EntradaForm(request.POST, instance=entrada)
        form.fields['idEvento'].queryset = eventos_permitidos

        if form.is_valid():
            entrada = form.save()
            EntradaActividad.objects.filter(idEntrada=entrada).delete()
            actividades = form.cleaned_data.get('actividades', [])
            for actividad in actividades:
                EntradaActividad.objects.create(idEntrada=entrada, idActividad=actividad)
            messages.success(request, 'La entrada se actualizó correctamente.')
            return redirect('listado_entradas')
        else:
            messages.error(request, 'Hubo un error al actualizar la entrada.')
    else:
        actividades_seleccionadas = entrada.actividades_incluidas.values_list('idActividad', flat=True)
        form = EntradaForm(instance=entrada, initial={
            'actividades': actividades_seleccionadas,
            'incluir_actividades': bool(actividades_seleccionadas),
        })
        form.fields['idEvento'].queryset = eventos_permitidos

    return render(request, 'entradas/editar.html', {
        'form': form,
        'entrada': entrada,
        'actividades_seleccionadas': list(actividades_seleccionadas)
    })

@login_required
@permiso_listado('entradas')
def detalles_entrada(request, idEntrada):
    entrada = get_object_or_404(Entrada, idEntrada=idEntrada)
    actividades = entrada.actividades_incluidas.all()

    return render(request, 'entradas/detalles.html', {
        'entrada': entrada,
        'actividades': actividades
    })

@login_required
@role_required(["super_administrador"])
def eliminar_entrada(request, idEntrada):
    entrada = get_object_or_404(Entrada, idEntrada=idEntrada)

    if request.method == 'POST':
        EntradaActividad.objects.filter(idEntrada=entrada).delete()
        entrada.delete()
        messages.success(request, 'La entrada ha sido eliminada correctamente.')
        return redirect('listado_entradas')

    messages.error(request, 'No se pudo eliminar la entrada.')
    return redirect('listado_entradas')

@login_required
@permiso_listado('compras_entradas')
def listar_compras_entradas(request):
    usuario = request.user
    compras = CompraEntrada.objects.select_related('usuario', 'entrada', 'entrada__idEvento')
    eventos_visibles = get_eventos_por_categoria(usuario, 'entradas')

    entradas_visibles = Entrada.objects.filter(idEvento__in=eventos_visibles)
    compras = compras.filter(entrada__in=entradas_visibles)

    q = request.GET.get('q')
    evento_id = request.GET.get('evento')
    entrada_id = request.GET.get('entrada')
    metodo_pago = request.GET.get('metodo_pago')

    if q:
        compras = compras.filter(Q(usuario__aNombre__icontains=q) | Q(usuario__aApellido__icontains=q) | Q(usuario__email__icontains=q))
    if evento_id:
        entradas_evento = entradas_visibles.filter(idEvento_id=evento_id)
        compras = compras.filter(entrada__in=entradas_evento)
    if entrada_id:
        compras = compras.filter(entrada_id=entrada_id)
    if metodo_pago:
        compras = compras.filter(metodo_pago=metodo_pago)

    return render(request, 'entradas/registro_entradas.html', {
        'compras': compras,
        'eventos': eventos_visibles,
        'entradas': entradas_visibles,
        'q': q,
        'evento_id': evento_id,
        'entrada_id': entrada_id,
        'metodo_pago': metodo_pago,
    })

@login_required
@permiso_listado('cupones_entrada')
def listar_cupones(request, idEntrada):
    entrada = get_object_or_404(Entrada, idEntrada=idEntrada)
    q = request.GET.get("q", "")
    cupones = Cupon.objects.filter(entrada=entrada)

    if q:
        cupones = cupones.filter(
            Q(aCodigo__icontains=q) |
            Q(nValor__icontains=q)
        )

    return render(request, "entradas/cupones/listado.html", {
        "cupones": cupones,
        "entrada": entrada,
        "q": q,
    })

@login_required
@permiso_o_superadmin_requerido('cupones_entrada', 'agregar')
def agregar_cupon(request, idEntrada):
    entrada = get_object_or_404(Entrada, idEntrada=idEntrada)

    if request.method == 'POST':
        form = CuponForm(request.POST)
        if form.is_valid():
            indicador = form.cleaned_data.get('indicador')
            cupon = form.save(commit=False)
            cupon.entrada = entrada
            cupon.aCodigo = generar_codigo(indicador)
            cupon.lActivo = True
            cupon.save()
            messages.success(request, f'Cupón {cupon.aCodigo} creado correctamente.')
            return redirect('listar_cupones', idEntrada=entrada.idEntrada)
        else:
            messages.error(request, 'Error al guardar el cupón.')
    else:
        form = CuponForm()

    return render(request, 'entradas/cupones/agregar.html', {
        'form': form,
        'entrada': entrada
    })

def generar_codigo(indicador=None):
    if indicador:
        base = indicador.upper()
        sufijo = ''.join(random.choices(string.ascii_uppercase + string.digits, k=7 - len(base)))
        return base + sufijo
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=7))

@login_required
@permiso_o_superadmin_requerido('cupones_entrada', 'desactivar')
def alternar_estado_cupon(request, id):
    cupon = get_object_or_404(Cupon, id=id)
    entrada = cupon.entrada
    if request.method == 'POST':
        cupon.lActivo = not cupon.lActivo
        cupon.save()
        if cupon.lActivo:
            messages.success(request, 'El cupon se activó correctamente.')
        else:
            messages.success(request, 'El cupon se desactivó correctamente.')
    return redirect('listar_cupones', idEntrada=entrada.idEntrada)

@login_required
@permiso_o_superadmin_requerido('cupones_entrada', 'editar')
def editar_cupon(request, id):
    cupon = get_object_or_404(Cupon, id=id)
    entrada = cupon.entrada

    if request.method == 'POST':
        form = CuponForm(request.POST, instance=cupon)
        if form.is_valid():

            form.save()
            messages.success(request, 'Cupón actualizado correctamente.')
            return redirect('listar_cupones', idEntrada=entrada.idEntrada)
        else:
            messages.error(request, 'Error al guardar los cambios.')
    else:
        form = CuponForm(instance=cupon)

    return render(request, 'entradas/cupones/editar.html', {
        'form': form,
        'cupon': cupon,
        'entrada': entrada
    })

@login_required
@permiso_listado('compras_entradas')
def listado_compras_efectivo(request):
    usuario = request.user
    eventos = get_eventos_por_categoria(usuario, 'entradas')
    eventos_ids = eventos.values_list('idEvento', flat=True).distinct()

    compras = CompraEntrada.objects.filter(
        metodo_pago='efectivo',
        status_pago='pendiente',
        entrada__idEvento__idEvento__in=eventos_ids
    ).select_related('usuario', 'entrada', 'entrada__idEvento')

    q = request.GET.get("q")
    evento_id = request.GET.get("evento")

    if q:
        compras = compras.filter(
            Q(usuario__aNombre__icontains=q) |
            Q(usuario__email__icontains=q) |
            Q(entrada__aNombre__icontains=q) |
            Q(referencia_pago__icontains=q)
        )

    if evento_id:
        compras = compras.filter(entrada__idEvento__idEvento=evento_id)

    compras = compras.order_by('-fecha_compra')

    return render(request, 'entradas/listado_efectivo.html', {
        'compras': compras,
        'eventos': eventos,
        'q': q,
        'evento_id': evento_id,
    })

@login_required
@permiso_o_superadmin_requerido('compras_entradas', 'marcar_pagadas')
def marcar_pago_efectivo(request, compra_id):
    compra = get_object_or_404(
        CompraEntrada,
        idCompra=compra_id,
        metodo_pago="efectivo",
        status_pago="pendiente"
    )
    compra.status_pago = "pagado"
    compra.save()

    entrada = compra.entrada

    if not entrada.lMultiple:
        entrada.nVendidas += 1
        entrada.save()

        if not RegistroEvento.objects.filter(usuario=compra.usuario, evento=entrada.idEvento).exists():
            RegistroEvento.objects.create(usuario=compra.usuario, evento=entrada.idEvento)

        for entrada_actividad in entrada.actividades_incluidas.all():
            actividad = entrada_actividad.idActividad
            if not RegistroActividad.objects.filter(usuario=compra.usuario, actividad=actividad).exists():
                RegistroActividad.objects.create(usuario=compra.usuario, actividad=actividad)
    else:
        entrada.nVendidas += compra.nCantidad
        entrada.save()

        for _ in range(compra.nCantidad):
            CodigoEntrada.objects.create(
                compra=compra,
                codigo=generar_codigo_unico()
            )

    enviar_correo_confirmacion(compra)
    messages.success(request, "Compra marcada como pagada.")
    return redirect("listado_compras_efectivo")
