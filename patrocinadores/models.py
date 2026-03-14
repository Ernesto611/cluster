from django.db import models
from usuarios.models import Usuario
from stands.models import Stand
from eventos.models import Evento
import os
import uuid
from datetime import datetime

def renombrar_archivo(instance, filename):
    ext = filename.split('.')[-1]
    fecha_hora = datetime.now().strftime('%Y%m%d%H%M%S')
    nombre = f"{fecha_hora}-{uuid.uuid4().hex}.{ext}"
    return os.path.join('patrocinadores/fotos/', nombre)

class Patrocinador(models.Model):
    idPatrocinador = models.AutoField(primary_key=True)
    aNombre = models.CharField(max_length=255, null=True, blank=True)
    aBiografia = models.TextField()
    aTelefono = models.CharField(max_length=20, null=True, blank=True)
    aWhatsapp = models.CharField(max_length=20, null=True, blank=True)
    aEmail = models.EmailField(null=True, blank=True)
    aFacebook = models.URLField(null=True, blank=True)
    aInstagram = models.URLField(null=True, blank=True)
    aTwitter = models.URLField(null=True, blank=True)
    aSitioWeb = models.URLField(null=True, blank=True)
    aFoto = models.ImageField(upload_to=renombrar_archivo, null=True, blank=True)
    lActivo = models.BooleanField(default=True)
    idStand = models.OneToOneField(Stand, on_delete=models.SET_NULL, null=True, blank=True, related_name="patrocinador")
    idEvento = models.ForeignKey(Evento, on_delete=models.CASCADE, related_name='patrocinadores', null=True, blank=True)

    def __str__(self):
        return self.idUsuario.aNombre
