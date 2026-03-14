import json
from datetime import datetime
from openpyxl import Workbook
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail, EmailMultiAlternatives
from django.db import transaction
from django.db.models import Count, Q
from django.http import JsonResponse, HttpResponse
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.html import strip_tags
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt
from django import forms
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from eventos.models import Evento, RegistroEvento
from actividades.models import Actividad, RegistroActividad, AcompañanteActividad
from stands.models import Stand, RegistroStand
from entradas.models import CompraEntrada, Entrada
from .models import Usuario, ConfiguracionExportacion, PermisoPersonalizado
from .forms import AdministradorForm, GestorForm, ConfiguracionExportacionForm
from .decorators import role_required
from utils.permisos import permiso_o_superadmin_requerido, permiso_listado, permisos_de_usuario, tiene_permiso_en_alguna_categoria, get_eventos_por_categoria, get_actividades_por_categoria, get_stands_por_categoria
from utils.filtrado_registros import get_registros_evento, get_registros_actividad, get_registros_stand

def enviar_correo_verificacion(usuario):
    token = usuario.token_verificacion
    link_verificacion = f"https://eventos.anadicmexico.mx{reverse('verificar_email', args=[token])}"

    context = {'usuario': usuario, 'link_verificacion': link_verificacion}
    html_content = render_to_string('web/email_verificacion.html', context)
    text_content = strip_tags(html_content)

    asunto = "Verifica tu cuenta en EVENTOS ANADICMX"
    email = EmailMultiAlternatives(asunto, text_content, 'verificacion@registroclustertim.com', [usuario.email])
    email.attach_alternative(html_content, "text/html")
    email.send()

@login_required
@permiso_listado(['registros_eventos', 'registros_actividades', 'registros_stands'])
def configurar_exportacion(request):
    config, _ = ConfiguracionExportacion.objects.get_or_create(usuario=request.user)

    if request.method == 'POST':
        form = ConfiguracionExportacionForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, 'Configuración guardada correctamente.')
            return redirect('configurar_exportacion')
    else:
        form = ConfiguracionExportacionForm(instance=config)

        if not tiene_permiso_en_alguna_categoria(request.user, ['registros_eventos']):
            del form.fields['exportar_eventos']

        if not tiene_permiso_en_alguna_categoria(request.user, ['registros_actividades']):
            del form.fields['exportar_actividades']

        if not tiene_permiso_en_alguna_categoria(request.user, ['registros_stands']):
            del form.fields['exportar_stands']

    return render(request, 'usuarios/configuracion_descargas.html', {'form': form})

@login_required
@permiso_listado('clientes')
def listar_clientes(request):
    q = request.GET.get('q', '')

    clientes = Usuario.objects.filter(tipo_usuario='cliente')

    if q:
        clientes = clientes.filter(
            Q(aNombre__icontains=q) |
            Q(aApellido__icontains=q) |
            Q(email__icontains=q) |
            Q(aEmpresa__icontains=q) |
            Q(aRFC__icontains=q)
        )

    clientes = clientes.annotate(
        eventos_asistidos=Count('eventos_registrados', filter=Q(eventos_registrados__status='escaneado'), distinct=True),
        actividades_asistidas=Count('actividades_registradas', filter=Q(actividades_registradas__status='escaneado'), distinct=True),
        stands_visitados=Count('stands_registradas', filter=Q(stands_registradas__status='escaneado'), distinct=True),
    )

    return render(request, 'usuarios/clientes/listado.html', {
        'clientes': clientes,
        'q': q,
    })

@login_required
@permiso_listado('usuarios')
def listar_administradores(request):
    usuario = request.user
    permisos = permisos_de_usuario(usuario, 'usuarios')

    usuarios = Usuario.objects.exclude(tipo_usuario='super_administrador').exclude(idUsuario=usuario.idUsuario)

    q = request.GET.get("q")
    if q:
        usuarios = usuarios.filter(
            Q(aNombre__icontains=q) |
            Q(aApellido__icontains=q) |
            Q(email__icontains=q) |
            Q(aAnadic__icontains=q)
        )

    tiene_permisos = request.GET.get("tiene_permisos")
    seccion = request.GET.get("seccion")

    if tiene_permisos in ['1', '0']:
        subquery = PermisoPersonalizado.objects.values('usuario')
        if tiene_permisos == '1':
            usuarios = usuarios.filter(idUsuario__in=subquery)
        else:
            usuarios = usuarios.exclude(idUsuario__in=subquery)

    if seccion:
        usuarios = usuarios.filter(permisos_personalizados__categoria=seccion).distinct()

    return render(request, 'usuarios/administradores/listado.html', {
        'administradores': usuarios,
        'q': q,
        'permisos': permisos,
        'tiene_permisos': tiene_permisos,
        'seccion': seccion,
        'PERMISOS_DEF': PERMISOS_DEF,
        'etiquetas_categorias': {
            "eventos": "Eventos",
            "registros_eventos": "Registros de Eventos",
            "actividades": "Actividades",
            "registros_actividades": "Registros de Actividades",
            "tipos_actividades": "Tipos de Actividades",
            "agendas": "Agendas",
            "conferencistas": "Conferencistas",
            "stands": "Stands",
            "registros_stands": "Registros de Stands",
            "horarios_citas": "Horarios de Citas",
            "citas": "Citas",
            "patrocinadores": "Patrocinadores",
            "entradas": "Entradas",
            "compras_entradas": "Compras de Entradas",
            "escanear_eventos": "Escanear entradas a eventos",
            "escanear_actividades": "Escanear entradas a actividades",
            "escanear_stands": "Escanear visitas a stands",
            "usuarios": "Usuarios",
            "banners": "Banners",
            "archivos_pagina": "Archivos de la Página",
        },
        'SUBSECCIONES': SUBSECCIONES,
    })

@login_required
@permiso_o_superadmin_requerido('usuarios', 'agregar')
def agregar_administrador(request):
    if request.method == 'POST':
        form = AdministradorForm(request.POST, request=request)
        if form.is_valid():
            if not form.cleaned_data.get('password'):
                messages.error(request, "La contraseña es obligatoria.")
            else:
                usuario = form.save()
                enviar_correo_verificacion(usuario)
                messages.success(request, "Administrador agregado correctamente. Se ha enviado un correo de verificación.")
                return redirect('asignar_permisos_usuario', idUsuario=usuario.idUsuario)
        else:
            messages.error(request, "Error al agregar administrador. Verifica los campos resaltados.")
    else:
        form = AdministradorForm(request=request)

    return render(request, 'usuarios/administradores/agregar.html', {'form': form})

@login_required
@permiso_listado('usuarios')
def detalles_usuario(request, idUsuario):
    usuario = get_object_or_404(Usuario, idUsuario=idUsuario)
    return render(request, 'usuarios/detalles.html', {
        'usuario_detalle': usuario
    })

PERMISOS_DEF = {
    "eventos": ["agregar", "editar", "desactivar"],
    "archivos_evento": ["agregar", "editar", "desactivar", "borrar"],
    "categorias_eventos":["agregar", "editar", "desactivar", "borrar", "editar_estilos"],
    "subcategorias_eventos":["agregar", "editar", "desactivar", "borrar"],
    "registros_eventos": ["ver"],
    "actividades": ["agregar", "editar", "desactivar"],
    "registros_actividades": ["ver"],
    "tipos_actividades": ["agregar", "editar", "desactivar"],
    "agendas": ["agregar", "editar", "desactivar"],
    "conferencistas": ["agregar", "editar"],
    "archivos_conferencista": ["agregar", "editar", "desactivar", "borrar"],
    "stands": ["agregar", "editar", "desactivar", "representante"],
    "productos_stand": ["agregar", "editar", "desactivar", "borrar", "representante"],
    "archivos_stand": ["agregar", "editar", "desactivar", "borrar", "representante"],
    "registros_stands": ["ver", "representante"],
    "horarios_citas": ["agregar", "desactivar", "representante"],
    "citas": ["editar", "representante"],
    "patrocinadores": ["agregar", "editar", "desactivar"],
    "entradas": ["agregar", "editar", "desactivar"],
    "cupones_entrada": ["agregar", "editar", "desactivar"],
    "compras_entradas": ["ver", "marcar_pagadas"],
    "aportaciones": ["agregar", "editar"],
    "aportadores": ["agregar", "editar", "desactivar"],
    "escanear_eventos": ["escanear"],
    "escanear_actividades": ["escanear"],
    "escanear_stands": ["escanear"],
    "banners": ["agregar", "editar", "desactivar", "borrar"],
    "archivos_pagina": ["agregar", "editar", "desactivar", "borrar"],
    "notificaciones": ["agregar", "editar", "enviar"],
    "datos_pago_efectivo": ["editar"],
    "usuarios": ["agregar", "editar", "desactivar", "editar_permisos"],
}

ALCANCES_POR_SECCION = {
    "eventos": ["estado", "evento"],
    "registros_eventos": ["estado", "evento"],
    "actividades": ["estado", "evento", "actividad"],
    "registros_actividades": ["estado", "evento", "actividad"],
    "agendas": ["estado", "evento"],
    "conferencistas": ["estado", "evento"],
    "stands": ["estado", "evento", "stand"],
    "registros_stands": ["estado", "evento", "stand"],
    "horarios_citas": ["estado", "evento", "stand"],
    "citas": ["estado", "evento", "stand"],
    "patrocinadores": ["estado", "evento"],
    "entradas": ["estado", "evento"],
    "aportaciones": ["estado", "evento"],
    "cupones_entrada": ["estado", "evento"],
    "compras_entradas": ["estado", "evento"],
    "escanear_eventos": ["estado", "evento"],
    "escanear_actividades": ["estado", "evento", "actividad"],
    "escanear_stands": ["estado", "evento", "stand"],
}

SUBSECCIONES = {
    "archivos_evento": "eventos",
    "productos_stand": "stands",
    "archivos_stand": "stands",
    "cupones_entrada": "entradas",
    "archivos_conferencista": "conferencistas",
}

ESTADOS_ANADIC = [estado for estado, _ in Usuario._meta.get_field('aAnadic').choices if estado != ""]

@permiso_o_superadmin_requerido('usuarios', ['agregar', 'editar_permisos'])
@transaction.atomic
def asignar_permisos_usuario(request, idUsuario):
    usuario = get_object_or_404(Usuario, idUsuario=idUsuario)

    if request.user.tipo_usuario == 'super_administrador':
        eventos = Evento.objects.all()
        stands = Stand.objects.all()
        actividades = Actividad.objects.all()
        estados = ESTADOS_ANADIC
    else:
        eventos = Evento.objects.filter(organizador__aAnadic=request.user.aAnadic)
        stands = Stand.objects.filter(idEvento__in=eventos)
        actividades = Actividad.objects.filter(idEvento__in=eventos)
        estados = [request.user.aAnadic]

    if request.method == "POST":
        PermisoPersonalizado.objects.filter(usuario=usuario).delete()
        nuevos_permisos = []

        for categoria, acciones in PERMISOS_DEF.items():
            acciones_seleccionadas = request.POST.getlist(f"acciones_{categoria}")
            if categoria in SUBSECCIONES:
                principal = SUBSECCIONES[categoria]
                alcance = request.POST.get(f"alcance_{principal}")
                valores = request.POST.getlist(f"valor_{principal}_{alcance}") if alcance else []
            else:
                alcance = request.POST.get(f"alcance_{categoria}")
                valores = request.POST.getlist(f"valor_{categoria}_{alcance}") if alcance else []

            valores_unicos = list(set(valores)) if valores else []

            for accion in acciones:
                if accion in acciones_seleccionadas:
                    if valores_unicos:
                        for valor in valores_unicos:
                            nuevos_permisos.append(PermisoPersonalizado(
                                usuario=usuario,
                                categoria=categoria,
                                accion=accion,
                                alcance=alcance,
                                valor=valor
                            ))
                    elif not alcance:
                        nuevos_permisos.append(PermisoPersonalizado(
                            usuario=usuario,
                            categoria=categoria,
                            accion=accion,
                            alcance=None,
                            valor=None
                        ))

        nuevos_permisos_unicos = {
            (p.usuario_id, p.categoria, p.accion, p.alcance, p.valor): p
            for p in nuevos_permisos
        }.values()

        PermisoPersonalizado.objects.bulk_create(nuevos_permisos_unicos)
        messages.success(request, "Permisos asignados correctamente.")
        return redirect('listar_administradores')

    etiquetas_categorias = {
        "eventos": "Eventos",
        "categorias_eventos":"Categorías de Eventos",
        "subcategorias_eventos":"Subategorías de Eventos",
        "archivos_evento": "Archivos de Evento",
        "registros_eventos": "Registros de Eventos",
        "actividades": "Actividades",
        "registros_actividades": "Registros de Actividades",
        "tipos_actividades": "Tipos de Actividades",
        "agendas": "Agendas",
        "conferencistas": "Conferencistas",
        "archivos_conferencista": "Archivos de Conferencista",
        "stands": "Stands",
        "productos_stand": "Productos de Stand",
        "archivos_stand": "Archivos de Stand",
        "registros_stands": "Registros de Stands",
        "horarios_citas": "Horarios de Citas",
        "citas": "Citas",
        "patrocinadores": "Patrocinadores",
        "entradas": "Entradas",
        "cupones_entrada": "Cupones de Entrada",
        "compras_entradas": "Compras de Entradas",
        "aportaciones": "Aportaciones",
        "aportadores": "Aportadores",
        "escanear_eventos": "Escanear entradas a eventos",
        "escanear_actividades": "Escanear entradas a actividades",
        "escanear_stands": "Escanear visitas a stands",
        "banners": "Banners",
        "archivos_pagina": "Archivos de la Página",
        "notificaciones": "Notificaciones",
        "datos_pago_efectivo": "Datos para pagos en efectivo",
        "usuarios": "Usuarios",
    }

    permisos_actuales = PermisoPersonalizado.objects.filter(usuario=usuario)

    permisos_marcados = {}
    alcances_marcados = {}

    for permiso in permisos_actuales:
        key = f"{permiso.categoria}|{permiso.accion}"
        permisos_marcados.setdefault(permiso.categoria, set()).add(permiso.accion)

        if permiso.categoria not in alcances_marcados:
            alcances_marcados[permiso.categoria] = {
                "alcance": permiso.alcance,
                "valores": set()
            }
        if permiso.valor:
            alcances_marcados[permiso.categoria]["valores"].add(permiso.valor)

    return render(request, 'usuarios/administradores/permisos.html', {
        "usuario": usuario,
        "permisos_def": PERMISOS_DEF,
        "alcances_por_seccion": ALCANCES_POR_SECCION,
        "etiquetas_categorias": etiquetas_categorias,
        "eventos": eventos,
        "stands": stands,
        "actividades": actividades,
        "estados": estados,
        "permisos_marcados": permisos_marcados,
        "alcances_marcados": alcances_marcados,
    })

@login_required
@permiso_o_superadmin_requerido('usuarios', 'editar')
def editar_administrador(request, idUsuario):
    usuario = get_object_or_404(Usuario, idUsuario=idUsuario)
    if request.method == 'POST':
        form = AdministradorForm(request.POST, instance=usuario)
        if form.is_valid():
            usuario_editado = form.save(commit=False)
            nueva_contraseña = form.cleaned_data.get('password')
            if nueva_contraseña:
                usuario_editado.set_password(nueva_contraseña)
            usuario_editado.save()
            messages.success(request, "Administrador editado correctamente.")
            return redirect('listar_administradores')
        else:
            messages.error(request, "Error al editar administrador. Verifica los campos.")
    else:
        form = AdministradorForm(instance=usuario)
        form.fields['password'].required = False

    return render(request, 'usuarios/administradores/editar.html', {
        'form': form,
        'usuario': usuario,
    })

@login_required
@permiso_o_superadmin_requerido('usuarios', 'desactivar')
def alternar_estado_usuario(request, idUsuario):
    usuario = get_object_or_404(Usuario, idUsuario=idUsuario)
    if request.method == 'POST':
        usuario.lActivo = not usuario.lActivo
        usuario.save()
        if usuario.lActivo:
            messages.success(request, 'El usuario se activó correctamente.')
        else:
            messages.success(request, 'El usuario se desactivó correctamente.')
    return redirect('listar_administradores')

@login_required
@role_required("super_administrador")
def eliminar_usuario(request, idUsuario):
    usuario = get_object_or_404(Usuario, idUsuario=idUsuario)
    if request.method == 'POST':
        if usuario.foto_perfil and os.path.isfile(usuario.foto_perfil.path):
            os.remove(usuario.foto_perfil.path)
        usuario.delete()
        messages.success(request, 'El usuario se eliminó correctamente.')
        return redirect('listar_administradores')
    return redirect('listar_administradores')

@login_required
@role_required(['super_administrador', 'administrador'])
def listar_gestores(request):
    q = request.GET.get("q")

    if request.user.tipo_usuario == 'super_administrador':
        gestores = Usuario.objects.filter(tipo_usuario='gestor')
    else:
        gestores = Usuario.objects.filter(tipo_usuario='gestor', aAnadic=request.user.aAnadic)

    if q:
        gestores = gestores.filter(
            Q(aNombre__icontains=q) |
            Q(aApellido__icontains=q) |
            Q(email__icontains=q) |
            Q(aAnadic__icontains=q)
        )

    return render(request, 'usuarios/gestores/listado.html', {
        'gestores': gestores,
        'q': q,
    })

@login_required
@role_required(['super_administrador', 'administrador'])
def agregar_gestor(request):
    if request.method == 'POST':
        form = GestorForm(request.POST, request=request)
        if form.is_valid():
            usuario = form.save()
            enviar_correo_verificacion(usuario)
            messages.success(request, "Gestor agregado correctamente. Se ha enviado un correo de verificación.")
            return redirect('listar_gestores')
        else:
            messages.error(request, "Error al agregar gestor. Verifica los campos resaltados.")
    else:
        form = GestorForm(request=request)

    return render(request, 'usuarios/gestores/agregar.html', {'form': form})

@login_required
@role_required(['super_administrador', 'administrador'])
def editar_gestor(request, idUsuario):
    usuario = get_object_or_404(Usuario, idUsuario=idUsuario, tipo_usuario='gestor')

    if request.method == 'POST':
        form = GestorForm(request.POST, instance=usuario, request=request)
        if form.is_valid():
            form.save()
            messages.success(request, "Gestor editado correctamente.")
            return redirect('listar_gestores')
        else:
            messages.error(request, "Error al editar gestor. Verifica los campos.")
    else:
        form = GestorForm(instance=usuario, request=request)
        form.fields['password'].required = False

    return render(request, 'usuarios/gestores/editar.html', {'form': form, 'usuario': usuario})

def validar_qr(qr_data):
    try:
        idUsuario, aQr = qr_data.split("+")
        usuario = Usuario.objects.filter(idUsuario=idUsuario, aQr=aQr).first()
        return usuario
    except ValueError:
        return None

def qr_no_valido(request, tipo):
    return render(request, "usuarios/lectores/qr_no_valido.html", {"tipo": tipo})

@csrf_exempt
@login_required
@permiso_listado('escanear_eventos')
def escaneo_evento(request):
    usuario = request.user

    eventos_activos = get_eventos_por_categoria(usuario, 'escanear_eventos').filter(lActivo=True)

    if request.method == "POST":
        try:
            data = json.loads(request.body)
            evento_id = data.get("evento_id")
            qr_data = data.get("qr_data")

            if not qr_data:
                return JsonResponse({"redirect_url": "/usuarios/qr_no_valido/evento/"})

            usuario_escaneado = validar_qr(qr_data)
            if not usuario_escaneado:
                return JsonResponse({"redirect_url": "/usuarios/qr_no_valido/evento/"})

            evento = get_object_or_404(Evento, idEvento=evento_id)

            if evento not in eventos_activos:
                return redirect("acceso_restringido")

            registro = RegistroEvento.objects.filter(usuario=usuario_escaneado, evento=evento).first()

            if registro:
                if registro.status == "pendiente":
                    registro.status = "escaneado"
                    registro.fEscaneo = now()
                    registro.escaneado_por = usuario
                    registro.save()
                    return JsonResponse({"redirect_url": f"/usuarios/entrada_registrada/{usuario_escaneado.idUsuario}/{evento.idEvento}/"})
                else:
                    return JsonResponse({"redirect_url": f"/usuarios/ya_registrado/{usuario_escaneado.idUsuario}/{evento.idEvento}/"})
            else:
                if evento.lGratuito:
                    RegistroEvento.objects.create(
                        usuario=usuario_escaneado, evento=evento, status="escaneado", fEscaneo=now(), escaneado_por=usuario
                    )
                    return JsonResponse({"redirect_url": f"/usuarios/entrada_registrada/{usuario_escaneado.idUsuario}/{evento.idEvento}/"})
                else:
                    return JsonResponse({"redirect_url": f"/usuarios/no_tiene_entrada/{usuario_escaneado.idUsuario}/{evento.idEvento}/"})

        except json.JSONDecodeError:
            return JsonResponse({"redirect_url": "/usuarios/qr_no_valido/evento/"})

    return render(request, "usuarios/lectores/escaneo_evento.html", {"eventos": eventos_activos})

def entrada_registrada(request, idUsuario, idEvento):
    usuario = get_object_or_404(Usuario, idUsuario=idUsuario)
    evento = get_object_or_404(Evento, idEvento=idEvento)
    return render(request, "usuarios/lectores/entrada_registrada.html", {"usuario": usuario, "evento": evento})

def ya_registrado(request, idUsuario, idEvento):
    usuario = get_object_or_404(Usuario, idUsuario=idUsuario)
    evento = get_object_or_404(Evento, idEvento=idEvento)
    return render(request, "usuarios/lectores/ya_registrado.html", {"usuario": usuario, "evento": evento})

def no_tiene_entrada(request, idUsuario, idEvento):
    usuario = get_object_or_404(Usuario, idUsuario=idUsuario)
    evento = get_object_or_404(Evento, idEvento=idEvento)
    return render(request, "usuarios/lectores/no_tiene_entrada.html", {"usuario": usuario, "evento": evento})

@csrf_exempt
@login_required
@permiso_listado('escanear_actividades')
def escaneo_actividad(request):
    usuario = request.user

    actividades_activas = get_actividades_por_categoria(usuario, 'escanear_actividades').filter(lActivo=True)

    if request.method == "POST":
        try:
            data = json.loads(request.body)
            actividad_id = data.get("actividad_id")
            qr_data = data.get("qr_data")

            if not qr_data:
                return JsonResponse({"redirect_url": "/usuarios/qr_no_valido/actividad/"})

            usuario_escaneado = validar_qr(qr_data)
            if not usuario_escaneado:
                return JsonResponse({"redirect_url": "/usuarios/qr_no_valido/actividad/"})

            actividad = get_object_or_404(Actividad, idActividad=actividad_id)

            if actividad not in actividades_activas:
                return redirect("acceso_restringido")

            registro = RegistroActividad.objects.filter(usuario=usuario_escaneado, actividad=actividad).first()

            if registro:
                if registro.status == "pendiente":
                    registro.status = "escaneado"
                    registro.fEscaneo = now()
                    registro.escaneado_por = usuario
                    registro.save()
                    return JsonResponse({"redirect_url": f"/usuarios/entrada_registrada_actividad/{usuario_escaneado.idUsuario}/{actividad.idActividad}/"})
                else:
                    return JsonResponse({"redirect_url": f"/usuarios/ya_registrado_actividad/{usuario_escaneado.idUsuario}/{actividad.idActividad}/"})
            else:
                if actividad.nCosto == 0:
                    if actividad.nLugaresDisponibles > 0:
                        actividad.nLugaresDisponibles -= 1
                        actividad.save()
                        RegistroActividad.objects.create(
                            usuario=usuario_escaneado, actividad=actividad, status="escaneado", fEscaneo=now(), escaneado_por=usuario
                        )
                        return JsonResponse({"redirect_url": f"/usuarios/entrada_registrada_actividad/{usuario_escaneado.idUsuario}/{actividad.idActividad}/"})
                    else:
                        return JsonResponse({"redirect_url": f"/usuarios/actividad_llena/{usuario_escaneado.idUsuario}/{actividad.idActividad}/"})
                else:
                    return JsonResponse({"redirect_url": f"/usuarios/no_tiene_entrada_actividad/{usuario_escaneado.idUsuario}/{actividad.idActividad}/"})

        except json.JSONDecodeError:
            return JsonResponse({"redirect_url": "/usuarios/qr_no_valido/actividad/"})

    return render(request, "usuarios/lectores/escaneo_actividad.html", {"actividades": actividades_activas})

def entrada_registrada_actividad(request, idUsuario, idActividad):
    usuario = get_object_or_404(Usuario, idUsuario=idUsuario)
    actividad = get_object_or_404(Actividad, idActividad=idActividad)
    acompanantes = AcompañanteActividad.objects.filter(registro__usuario=usuario, registro__actividad=actividad)
    return render(request, "usuarios/lectores/entrada_registrada_actividad.html", {"usuario": usuario, "actividad": actividad, "acompanantes": acompanantes})

def ya_registrado_actividad(request, idUsuario, idActividad):
    usuario = get_object_or_404(Usuario, idUsuario=idUsuario)
    actividad = get_object_or_404(Actividad, idActividad=idActividad)
    return render(request, "usuarios/lectores/ya_registrado_actividad.html", {"usuario": usuario, "actividad": actividad})

def no_tiene_entrada_actividad(request, idUsuario, idActividad):
    usuario = get_object_or_404(Usuario, idUsuario=idUsuario)
    actividad = get_object_or_404(Actividad, idActividad=idActividad)
    return render(request, "usuarios/lectores/no_tiene_entrada_actividad.html", {"usuario": usuario, "actividad": actividad})

def actividad_llena(request, idUsuario, idActividad):
    usuario = get_object_or_404(Usuario, idUsuario=idUsuario)
    actividad = get_object_or_404(Actividad, idActividad=idActividad)
    return render(request, "usuarios/lectores/actividad_llena.html", {"usuario": usuario, "actividad": actividad})

@csrf_exempt
@login_required
@permiso_listado('escanear_stands')
def escaneo_stand(request):
    usuario = request.user

    stands_activos = get_stands_por_categoria(usuario, 'escanear_stands').filter(lActivo=True)

    if request.method == "POST":
        try:
            data = json.loads(request.body)
            stand_id = data.get("stand_id")
            qr_data = data.get("qr_data")

            if not qr_data:
                return JsonResponse({"redirect_url": "/usuarios/qr_no_valido/stand/"})

            usuario_escaneado = validar_qr(qr_data)
            if not usuario_escaneado:
                return JsonResponse({"redirect_url": "/usuarios/qr_no_valido/stand/"})

            stand = get_object_or_404(Stand, idStand=stand_id)

            if stand not in stands_activos:
                return redirect("acceso_restringido")

            registro = RegistroStand.objects.filter(usuario=usuario_escaneado, stand=stand).first()

            if registro:
                if registro.status == "escaneado":
                    return JsonResponse({"redirect_url": f"/usuarios/ya_visitado_stand/{usuario_escaneado.idUsuario}/{stand.idStand}/"})
            else:
                RegistroStand.objects.create(
                    usuario=usuario_escaneado, stand=stand, status="escaneado", fEscaneo=now(), escaneado_por=usuario
                )
                return JsonResponse({"redirect_url": f"/usuarios/visita_registrada_stand/{usuario_escaneado.idUsuario}/{stand.idStand}/"})

        except json.JSONDecodeError:
            return JsonResponse({"redirect_url": "/usuarios/qr_no_valido/stand/"})

    return render(request, "usuarios/lectores/escaneo_stand.html", {"stands": stands_activos})

def visita_registrada_stand(request, idUsuario, idStand):
    usuario = get_object_or_404(Usuario, idUsuario=idUsuario)
    stand = get_object_or_404(Stand, idStand=idStand)
    return render(request, "usuarios/lectores/visita_registrada_stand.html", {"usuario": usuario, "stand": stand})

def ya_visitado_stand(request, idUsuario, idStand):
    usuario = get_object_or_404(Usuario, idUsuario=idUsuario)
    stand = get_object_or_404(Stand, idStand=idStand)
    return render(request, "usuarios/lectores/ya_visitado_stand.html", {"usuario": usuario, "stand": stand})

def _generar_excel(request, registros, columnas, nombre_archivo):
    wb = Workbook()
    ws = wb.active
    ws.append(columnas)

    for fila in registros:
        ws.append(fila)

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{nombre_archivo}"'
    wb.save(response)
    return response

@login_required
def descargar_excel_eventos(request):
    registros = get_registros_evento(request.user)
    data = [
        [r.usuario.aNombre, r.usuario.aApellido, r.usuario.email, r.evento.aNombre, r.status, r.fRegistro.strftime('%d/%m/%Y %H:%M')]
        for r in registros
    ]
    return _generar_excel(request, data, ['Nombre', 'Apellido/s', 'Correo', 'Evento', 'Estado', 'Fecha'], 'registros_eventos.xlsx')

@login_required
def descargar_excel_actividades(request):
    registros = get_registros_actividad(request.user)
    data = [
        [r.usuario.aNombre, r.usuario.aApellido, r.usuario.email, r.actividad.idEvento.aNombre, r.actividad.aNombre, r.status, r.fRegistro.strftime('%d/%m/%Y %H:%M')]
        for r in registros
    ]
    return _generar_excel(request, data, ['Nombre', 'Apellido/s', 'Correo', 'Evento', 'Actividad', 'Estado', 'Fecha'], 'registros_actividades.xlsx')

@login_required
def descargar_excel_stands(request):
    registros = get_registros_stand(request.user)
    data = [
        [r.usuario.aNombre, r.usuario.aApellido, r.usuario.email, r.stand.idEvento.aNombre, r.stand.aNombre, r.status, r.fRegistro.strftime('%d/%m/%Y %H:%M')]
        for r in registros
    ]
    return _generar_excel(request, data, ['Nombre', 'Apellido/s', 'Correo', 'Evento', 'Stand', 'Estado', 'Fecha'], 'registros_stands.xlsx')
