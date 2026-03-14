from django.db import models
from usuarios.models import Usuario
from actividades.models import Actividad
import os
import uuid
from datetime import datetime
from django.core.exceptions import ValidationError

def archivo_expositor_upload_path(instance, filename):
    ext = filename.split('.')[-1]
    new_filename = f"{uuid.uuid4().hex}.{ext}"
    return os.path.join("expositores", "descargas", str(instance.expositor.idExpositor), new_filename)

def validar_extension_archivo(valor):
    ext_permitidas = ['.pdf', '.docx', '.pptx', '.xls', '.xlsx', '.jpg', '.jpeg', '.png', '.mp4']
    ext = os.path.splitext(valor.name)[1].lower()
    if ext not in ext_permitidas:
        raise ValidationError(f'Formato de archivo no permitido: {ext}')

class Expositor(models.Model):
    idExpositor = models.AutoField(primary_key=True)
    aNombre = models.CharField(max_length=255, null=True, blank=True)
    aBiografia = models.TextField()
    aTelefono = models.CharField(max_length=20, null=True, blank=True)
    aWhatsapp = models.CharField(max_length=20, null=True, blank=True)
    aEmail = models.EmailField(null=True, blank=True)
    aFacebook = models.URLField(null=True, blank=True)
    aInstagram = models.URLField(null=True, blank=True)
    aTwitter = models.URLField(null=True, blank=True)
    aSitioWeb = models.URLField(null=True, blank=True)
    aFoto = models.ImageField(upload_to='expositores/fotos/', null=True, blank=True)
    lActivo = models.BooleanField(default=True)

    def __str__(self):
        return self.aNombre

class ExpositorActividad(models.Model):
    idExpositorActividad = models.AutoField(primary_key=True)
    idExpositor = models.ForeignKey(Expositor, on_delete=models.CASCADE, related_name="actividades")
    idActividad = models.ForeignKey(Actividad, on_delete=models.CASCADE, related_name="expositores")

    def __str__(self):
        return f"{self.idExpositor.idUsuario.aNombre} - {self.idActividad.aNombre}"

class ArchivoExpositor(models.Model):
    expositor = models.ForeignKey("Expositor", on_delete=models.CASCADE, related_name="archivos")
    titulo = models.CharField(max_length=255)
    archivo = models.FileField(upload_to=archivo_expositor_upload_path, validators=[validar_extension_archivo])
    fecha_subida = models.DateTimeField(auto_now_add=True)
    lActivo = models.BooleanField(default=True)

    def __str__(self):
        return self.titulo
