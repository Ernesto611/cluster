from eventos.models import Evento, ArchivoEvento
from web.models import ArchivoPagina
from django.conf import settings
import os
from eventos.models import CategoriaEvento, SubcategoriaEvento
from usuarios.models import PermisoPersonalizado
from django.db.models import Prefetch
from utils.fechas import ahora_mx

def branding(request):

    return {
        "navbar_logo_url": request.session.get("navbar_logo_url")
    }

def fecha_mexicana(request):
    return {
        'ahora_mx': ahora_mx(),
    }

def ultimo_evento_context(request):
    evento_principal_id = getattr(settings, 'EVENTO_PRINCIPAL_ID', None)
    ultimo_evento_id = request.session.get('ultimo_evento_id', evento_principal_id)
    return {'ultimo_evento_id': ultimo_evento_id}

def eventos_context(request):
    return {'eventos_activos': Evento.objects.filter(lActivo=True)}

def archivos_descargables_context(request):
    archivos = []
    archivos_queryset = ArchivoPagina.objects.all()
    for archivo in archivos_queryset:
        ext = os.path.splitext(archivo.archivo.name)[1]
        archivo.extension = ext[1:].upper() if ext else ''
        archivos.append(archivo)

    return {'archivos_descargables': archivos}

def archivos_descargables_evento_context(request):
    evento_principal_id = getattr(settings, 'EVENTO_PRINCIPAL_ID', None)
    ultimo_evento_id = request.session.get('ultimo_evento_id', evento_principal_id)

    archivos = []
    if ultimo_evento_id:
        archivos_queryset = ArchivoEvento.objects.filter(evento__idEvento=ultimo_evento_id)
        for archivo in archivos_queryset:
            ext = os.path.splitext(archivo.archivo.name)[1]
            archivo.extension = ext[1:].upper() if ext else ''
            archivos.append(archivo)

    return {'archivos_descargables_evento': archivos}

def categorias_eventos_context(request):
    categorias = CategoriaEvento.objects.filter(lActivo=True).prefetch_related(
        Prefetch('subcategorias', queryset=SubcategoriaEvento.objects.filter(lActivo=True).prefetch_related(
            Prefetch('eventos', queryset=Evento.objects.filter(lActivo=True))
        ))
    )

    categorias_con_subcategorias = []

    for categoria in categorias:
        subcategorias_validas = []
        for sub in categoria.subcategorias.all():
            if sub.eventos.exists():
                subcategorias_validas.append({
                    'nombre': sub.aNombre,
                    'eventos': sub.eventos.all()
                })

        if subcategorias_validas:
            categorias_con_subcategorias.append({
                'nombre': categoria.aNombre,
                'subcategorias': subcategorias_validas
            })

    return {'categorias_eventos': categorias_con_subcategorias}

def permisos_por_categoria(request):
    user = request.user
    permisos = {}

    if not user.is_authenticated:
        return {"permisos_categoria": permisos}

    if getattr(user, 'tipo_usuario', '') == 'super_administrador':

        return {
            "permisos_categoria": {
                "todos": True
            }
        }

    permisos_usuario = PermisoPersonalizado.objects.filter(usuario=user).values_list('categoria', flat=True).distinct()

    for categoria in permisos_usuario:
        permisos[categoria] = True

    return {
        "permisos_categoria": permisos
    }
