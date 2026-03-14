from eventos.models import RegistroEvento, Evento
from actividades.models import RegistroActividad, Actividad
from stands.models import RegistroStand, Stand
from usuarios.models import PermisoPersonalizado

def get_valores_permiso(usuario, categoria):
    if usuario.tipo_usuario == 'super_administrador':
        return {'todos': True}

    permisos = PermisoPersonalizado.objects.filter(
        usuario=usuario,
        categoria=categoria,
        accion='ver'
    )

    resultado = {
        'estado': set(),
        'evento': set(),
        'actividad': set(),
        'stand': set()
    }

    for permiso in permisos:
        if permiso.alcance and permiso.valor:
            resultado[permiso.alcance].add(permiso.valor)

    return resultado

def get_registros_evento(usuario):
    if usuario.tipo_usuario == 'super_administrador':
        return RegistroEvento.objects.select_related('usuario', 'evento').all()

    permisos = get_valores_permiso(usuario, 'registros_eventos')
    registros = RegistroEvento.objects.select_related('usuario', 'evento')

    if permisos.get('todos'):
        return registros

    filtro = Q()
    if permisos['estado']:
        filtro |= Q(evento__organizador__aAnadic__in=permisos['estado'])
    if permisos['evento']:
        filtro |= Q(evento__idEvento__in=permisos['evento'])

    return registros.filter(filtro)

def get_registros_actividad(usuario):
    if usuario.tipo_usuario == 'super_administrador':
        return RegistroActividad.objects.select_related('usuario', 'actividad', 'actividad__idEvento').all()

    permisos = get_valores_permiso(usuario, 'registros_actividades')
    registros = RegistroActividad.objects.select_related('usuario', 'actividad', 'actividad__idEvento')

    if permisos.get('todos'):
        return registros

    filtro = Q()
    if permisos['estado']:
        filtro |= Q(actividad__idEvento__organizador__aAnadic__in=permisos['estado'])
    if permisos['evento']:
        filtro |= Q(actividad__idEvento__idEvento__in=permisos['evento'])
    if permisos['actividad']:
        filtro |= Q(actividad__idActividad__in=permisos['actividad'])

    return registros.filter(filtro)

def get_registros_stand(usuario):
    if usuario.tipo_usuario == 'super_administrador':
        return RegistroStand.objects.select_related('usuario', 'stand', 'stand__idEvento').all()

    permisos = get_valores_permiso(usuario, 'registros_stands')
    registros = RegistroStand.objects.select_related('usuario', 'stand', 'stand__idEvento')

    if permisos.get('todos'):
        return registros

    filtro = Q()
    if permisos['estado']:
        filtro |= Q(stand__idEvento__organizador__aAnadic__in=permisos['estado'])
    if permisos['evento']:
        filtro |= Q(stand__idEvento__idEvento__in=permisos['evento'])
    if permisos['stand']:
        filtro |= Q(stand__idStand__in=permisos['stand'])

    return registros.filter(filtro)
