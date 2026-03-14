from functools import wraps
from django.shortcuts import redirect
from usuarios.models import PermisoPersonalizado
from eventos.models import Evento
from actividades.models import Actividad
from stands.models import Stand
from django.db.models import Q

def es_super_administrador(u):
    return getattr(u, "tipo_usuario", None) == "super_administrador"

def permiso_listado_cualquiera(categorias):
    if isinstance(categorias, str):
        categorias = [categorias]

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            user = request.user

            if getattr(user, 'tipo_usuario', '') == 'super_administrador':
                return view_func(request, *args, **kwargs)

            tiene_permiso = PermisoPersonalizado.objects.filter(
                usuario=user,
                categoria__in=categorias
            ).exists()

            if tiene_permiso:
                return view_func(request, *args, **kwargs)

            return redirect('acceso_restringido')
        return _wrapped_view
    return decorator

def tiene_accion_listar(perms):
    if isinstance(perms, (set, list, tuple)):
        return ('listar' in perms) or ('ver' in perms) or ('*' in perms)
    if isinstance(perms, dict):
        return perms.get('listar') or perms.get('ver') or perms.get('*')
    return bool(perms)

def permiso_o_superadmin_requerido(categoria, acciones):
    if isinstance(acciones, str):
        acciones = [acciones]

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            user = request.user

            if getattr(user, 'tipo_usuario', '') == 'super_administrador':
                return view_func(request, *args, **kwargs)

            tiene_permiso = PermisoPersonalizado.objects.filter(
                usuario=user,
                categoria=categoria,
                accion__in=acciones
            ).exists()

            if tiene_permiso:
                return view_func(request, *args, **kwargs)

            return redirect('acceso_restringido')
        return _wrapped_view
    return decorator

def permiso_o_superadmin_requerido(categoria, acciones):
    if isinstance(acciones, str):
        acciones = [acciones]

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            user = request.user

            if getattr(user, 'tipo_usuario', '') == 'super_administrador':
                return view_func(request, *args, **kwargs)

            tiene_permiso = PermisoPersonalizado.objects.filter(
                usuario=user,
                categoria=categoria,
                accion__in=acciones
            ).exists()

            if tiene_permiso:
                return view_func(request, *args, **kwargs)

            return redirect('acceso_restringido')
        return _wrapped_view
    return decorator

def permiso_stands_acciones_o_representante(acciones):

    if isinstance(acciones, str):
        acciones = [acciones]

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            user = request.user

            if getattr(user, 'tipo_usuario', '') == 'super_administrador':
                return view_func(request, *args, **kwargs)

            tiene_accion = PermisoPersonalizado.objects.filter(
                usuario=user,
                categoria='stands',
                accion__in=acciones
            ).exists()

            es_representante = PermisoPersonalizado.objects.filter(
                usuario=user,
                categoria='stands',
                accion='representante'
            ).exists()

            if tiene_accion or es_representante:
                return view_func(request, *args, **kwargs)

            return redirect('acceso_restringido')
        return _wrapped_view
    return decorator

def permiso_archivos_stand_accion_o_representante(accion):

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            user = request.user
            if es_super_administrador(user):
                return view_func(request, *args, **kwargs)

            tiene_accion = PermisoPersonalizado.objects.filter(
                usuario=user, categoria='archivos_stand', accion=accion
            ).exists()
            if tiene_accion:
                return view_func(request, *args, **kwargs)

            if tiene_permiso_representante(user, 'stands'):
                archivo_id = kwargs.get('id_archivo') or kwargs.get('id') or kwargs.get('archivo_id')
                if archivo_id:
                    archivo = ArchivoStand.objects.select_related('stand').filter(id=archivo_id).first()
                    if archivo and archivo.stand and archivo.stand.representante_id == getattr(user, 'idUsuario', None):
                        return view_func(request, *args, **kwargs)

            return redirect('acceso_restringido')
        return _wrapped_view
    return decorator

def permiso_productos_stand_accion_o_representante(accion):

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            user = request.user
            if es_super_administrador(user):
                return view_func(request, *args, **kwargs)

            if PermisoPersonalizado.objects.filter(
                usuario=user, categoria='productos_stand', accion=accion
            ).exists():
                return view_func(request, *args, **kwargs)

            if tiene_permiso_representante(user, 'stands'):
                stand_id = kwargs.get('idStand') or kwargs.get('stand_id') or kwargs.get('id_stand')
                if stand_id:
                    stand = Stand.objects.filter(idStand=stand_id).only('representante_id').first()
                    if stand and stand.representante_id == getattr(user, 'idUsuario', None):
                        return view_func(request, *args, **kwargs)

            return redirect('acceso_restringido')
        return _wrapped_view
    return decorator

def permiso_producto_accion_o_representante(accion):

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            user = request.user
            if es_super_administrador(user):
                return view_func(request, *args, **kwargs)

            if PermisoPersonalizado.objects.filter(
                usuario=user, categoria='productos_stand', accion=accion
            ).exists():
                return view_func(request, *args, **kwargs)

            if tiene_permiso_representante(user, 'stands'):
                prod_id = kwargs.get('idProducto') or kwargs.get('producto_id') or kwargs.get('id')
                if prod_id:
                    producto = Producto.objects.select_related('idStand').filter(idProducto=prod_id).first()
                    if producto and producto.idStand and producto.idStand.representante_id == getattr(user, 'idUsuario', None):
                        return view_func(request, *args, **kwargs)

            return redirect('acceso_restringido')
        return _wrapped_view
    return decorator

def permiso_listado(categorias):
    if isinstance(categorias, str):
        categorias = [categorias]

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            user = request.user

            if getattr(user, 'tipo_usuario', '') == 'super_administrador':
                return view_func(request, *args, **kwargs)

            tiene_permiso = PermisoPersonalizado.objects.filter(
                usuario=user,
                categoria__in=categorias
            ).exists()

            if tiene_permiso:
                return view_func(request, *args, **kwargs)

            return redirect('acceso_restringido')
        return _wrapped_view
    return decorator

def permisos_de_usuario(usuario, categoria):
    if getattr(usuario, 'tipo_usuario', '') == 'super_administrador':
        return {'*'}

    return set(
        PermisoPersonalizado.objects
        .filter(usuario=usuario, categoria=categoria)
        .values_list('accion', flat=True)
    )

def tiene_permiso_en_alguna_categoria(usuario, categorias):
    if getattr(usuario, 'tipo_usuario', '') == 'super_administrador':
        return True

    return PermisoPersonalizado.objects.filter(usuario=usuario, categoria__in=categorias).exists()

def get_eventos_por_categoria(usuario, categoria):

    if usuario.tipo_usuario == 'super_administrador':
        return Evento.objects.all()

    permisos = PermisoPersonalizado.objects.filter(usuario=usuario, categoria=categoria)

    if permisos.filter(alcance='estado', valor__iexact='Nacional').exists():
        return Evento.objects.all()

    estados = list(
        permisos.filter(alcance='estado')
                .exclude(valor__isnull=True).exclude(valor='')
                .values_list('valor', flat=True)
    )
    eventos_ids = list(
        permisos.filter(alcance='evento')
                .exclude(valor__isnull=True).exclude(valor='')
                .values_list('valor', flat=True)
    )

    filtros = Q()
    if estados:
        filtros |= Q(organizador__aAnadic__in=estados)
    if eventos_ids:
        filtros |= Q(idEvento__in=eventos_ids)

    return Evento.objects.filter(filtros).distinct() if filtros else Evento.objects.none()

def get_actividades_por_categoria(usuario, categoria):

    if usuario.tipo_usuario == 'super_administrador':
        return Actividad.objects.all()

    permisos = PermisoPersonalizado.objects.filter(usuario=usuario, categoria=categoria)

    if permisos.filter(alcance='estado', valor__iexact='Nacional').exists():
        return Actividad.objects.all()

    estados = list(
        permisos.filter(alcance='estado')
                .exclude(valor__isnull=True).exclude(valor='')
                .values_list('valor', flat=True)
    )
    eventos_ids = list(
        permisos.filter(alcance='evento')
                .exclude(valor__isnull=True).exclude(valor='')
                .values_list('valor', flat=True)
    )
    actividades_ids = list(
        permisos.filter(alcance='actividad')
                .exclude(valor__isnull=True).exclude(valor='')
                .values_list('valor', flat=True)
    )

    filtros = Q()
    if estados:
        filtros |= Q(idEvento__organizador__aAnadic__in=estados)
    if eventos_ids:
        filtros |= Q(idEvento__in=eventos_ids)
    if actividades_ids:
        filtros |= Q(idActividad__in=actividades_ids)

    return Actividad.objects.filter(filtros).distinct() if filtros else Actividad.objects.none()

def tiene_permiso_representante(usuario, categoria='stands'):
    return PermisoPersonalizado.objects.filter(
        usuario=usuario, categoria=categoria, accion='representante'
    ).exists()

def stands_representados_qs(usuario):

    return Stand.objects.filter(representante=usuario)

def get_stands_por_categoria(usuario, categoria):
    if getattr(usuario, 'tipo_usuario', '') == 'super_administrador':
        return Stand.objects.all()

    permisos = PermisoPersonalizado.objects.filter(usuario=usuario, categoria=categoria)

    ids_stands = set()

    for permiso in permisos:
        if permiso.alcance == 'empresa' and permiso.valor:
            ids_stands.update(
                Stand.objects.filter(idEvento__empresa_id=permiso.valor).values_list('idStand', flat=True)
            )
        elif permiso.alcance == 'evento' and permiso.valor:
            ids_stands.update(
                Stand.objects.filter(idEvento=permiso.valor).values_list('idStand', flat=True)
            )
        elif permiso.alcance == 'stand' and permiso.valor:
            try:
                ids_stands.add(int(permiso.valor))
            except (TypeError, ValueError):
                pass

    qs = Stand.objects.filter(idStand__in=list(ids_stands))

    if tiene_permiso_representante(usuario, categoria='stands'):
        qs_rep = stands_representados_qs(usuario).values_list('idStand', flat=True)
        qs = Stand.objects.filter(idStand__in=set(list(qs.values_list('idStand', flat=True)) + list(qs_rep)))

    return qs

def get_alcance_categoria(usuario, categoria):
    permiso = PermisoPersonalizado.objects.filter(usuario=usuario, categoria=categoria).first()
    return permiso.alcance if permiso else None
