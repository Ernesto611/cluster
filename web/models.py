from django.db import models
from django.core.exceptions import ValidationError
import os
import uuid
from utils.fechas import ahora_mx

def banner_imagen_upload_path(instance, filename):
    ext = filename.split('.')[-1]
    nombre = ahora_mx().strftime('%Y%m%d%H%M%S%f')
    return f'banners/{nombre}.{ext}'

def archivo_upload_path(instance, filename):
    ext = filename.split('.')[-1]
    new_filename = f"{uuid.uuid4().hex}.{ext}"
    return os.path.join("descargas", new_filename)

def validar_extension_archivo(valor):
    ext_permitidas = ['.pdf', '.docx', '.pptx', '.xls', '.xlsx', '.jpg', '.jpeg', '.png', '.mp4']
    ext = os.path.splitext(valor.name)[1].lower()
    if ext not in ext_permitidas:
        raise ValidationError(f'Formato de archivo no permitido: {ext}')

class BannerPrincipal(models.Model):
    titulo = models.CharField(max_length=255)
    url = models.URLField(blank=True, null=True)
    imagen = models.ImageField(upload_to=banner_imagen_upload_path)
    creado = models.DateTimeField()
    lActivo = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.pk and not self.creado:
            self.creado = ahora_mx()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.titulo

class ArchivoPagina(models.Model):
    titulo = models.CharField(max_length=255)
    archivo = models.FileField(upload_to=archivo_upload_path, validators=[validar_extension_archivo])
    fecha_subida = models.DateTimeField()
    lActivo = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.pk and not self.fecha_subida:
            self.fecha_subida = ahora_mx()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.titulo

class DatosPagoEfectivoConfiguracion(models.Model):
    aNombreBanco = models.CharField("Nombre del banco", max_length=100)
    aNombreBeneficiario = models.CharField("Nombre del beneficiario", max_length=255)
    aNumeroCuenta = models.CharField("Número de cuenta", max_length=50)
    aClabe = models.CharField("CLABE interbancaria", max_length=50)
    lActivo = models.BooleanField(default=True, help_text="Indica si este método está disponible actualmente")

    def __str__(self):
        return f"{self.aNombreBanco} - {self.aNombreBeneficiario}"
