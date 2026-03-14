from django.db import models
from usuarios.models import Usuario
import os
import uuid
from datetime import datetime
from django.core.exceptions import ValidationError
from utils.fechas import ahora_mx

def archivo_evento_upload_path(instance, filename):
    ext = filename.split('.')[-1]
    new_filename = f"{uuid.uuid4().hex}.{ext}"
    return os.path.join("eventos", "descargas", str(instance.evento.idEvento), new_filename)

def validar_extension_archivo(valor):
    ext_permitidas = ['.pdf', '.docx', '.pptx', '.xls', '.xlsx', '.jpg', '.jpeg', '.png', '.mp4']
    ext = os.path.splitext(valor.name)[1].lower()
    if ext not in ext_permitidas:
        raise ValidationError(f'Formato de archivo no permitido: {ext}')

def renombrar_archivo(instance, filename):
    ext = filename.split('.')[-1]
    fecha_hora = datetime.now().strftime('%Y%m%d%H%M%S')
    nombre = f"{fecha_hora}-{uuid.uuid4().hex}.{ext}"
    return os.path.join('eventos/imagenes/', nombre)

def categoria_logo_upload_path(instance, filename):
    base, ext = os.path.splitext(filename)
    if not ext:
        ext = ".png"
    slug = slugify(instance.aNombre) or f"categoria-{instance.idCategoria}"
    ts = int(time.time())
    return f"categorias/logos/{slug}_{ts}{ext.lower()}"

class CategoriaEvento(models.Model):
    idCategoria = models.AutoField(primary_key=True)
    aNombre = models.CharField(max_length=255, unique=True)
    lActivo = models.BooleanField(default=True)

    estilo_detalle_evento = models.CharField(
        max_length=1,
        choices=[('1', 'Estilo 1'), ('2', 'Estilo 2')],
        default='1'
    )
    logo = models.ImageField(upload_to=categoria_logo_upload_path, null=True, blank=True)

    def __str__(self):
        return self.aNombre

class SubcategoriaEvento(models.Model):
    categoria = models.ForeignKey(CategoriaEvento, on_delete=models.SET_NULL, null=True, related_name='subcategorias')
    aNombre = models.CharField(max_length=255, unique=True)
    lActivo = models.BooleanField(default=True)

    def __str__(self):
        return self.aNombre

class Evento(models.Model):
    idEvento = models.AutoField(primary_key=True)
    aNombre = models.CharField(max_length=255)
    aDescripcion = models.TextField()
    fFechaInicio = models.DateTimeField()
    fFechaFin = models.DateTimeField()
    dCalle = models.CharField(max_length=255, default="No especificado")
    dNumero = models.CharField(max_length=10, default="S/N")
    dColonia = models.CharField(max_length=255, default="No especificado")
    dCiudad = models.CharField(max_length=255, default="No especificado")
    dEstado = models.CharField(
        max_length=50,
        choices=[
            ("Aguascalientes", "Aguascalientes"),
            ("Baja California", "Baja California"),
            ("Baja California Sur", "Baja California Sur"),
            ("Campeche", "Campeche"),
            ("Chiapas", "Chiapas"),
            ("Chihuahua", "Chihuahua"),
            ("Coahuila", "Coahuila"),
            ("Colima", "Colima"),
            ("Ciudad de México", "Ciudad de México"),
            ("Durango", "Durango"),
            ("Estado de México", "Estado de México"),
            ("Guanajuato", "Guanajuato"),
            ("Guerrero", "Guerrero"),
            ("Hidalgo", "Hidalgo"),
            ("Jalisco", "Jalisco"),
            ("Michoacán", "Michoacán"),
            ("Morelos", "Morelos"),
            ("Nayarit", "Nayarit"),
            ("Nuevo León", "Nuevo León"),
            ("Oaxaca", "Oaxaca"),
            ("Puebla", "Puebla"),
            ("Querétaro", "Querétaro"),
            ("Quintana Roo", "Quintana Roo"),
            ("San Luis Potosí", "San Luis Potosí"),
            ("Sinaloa", "Sinaloa"),
            ("Sonora", "Sonora"),
            ("Tabasco", "Tabasco"),
            ("Tamaulipas", "Tamaulipas"),
            ("Tlaxcala", "Tlaxcala"),
            ("Veracruz", "Veracruz"),
            ("Yucatán", "Yucatán"),
            ("Zacatecas", "Zacatecas"),
        ],
        default="No especificado"
    )
    dCP = models.CharField(max_length=10, default="00000")

    dLatitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    dLongitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    categoria = models.ForeignKey(CategoriaEvento, on_delete=models.SET_NULL, null=True, related_name='eventos')
    subcategoria = models.ForeignKey(SubcategoriaEvento, on_delete=models.SET_NULL, null=True, related_name='eventos')
    lGratuito = models.BooleanField(default=False)
    aImagen = models.ImageField(upload_to=renombrar_archivo, null=True, blank=True)
    lAgendaVisible = models.BooleanField(default=True)
    lActivo = models.BooleanField(default=True)

    organizador = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='eventos'
    )

    def __str__(self):
        return self.aNombre

    def clean(self):
        if self.subcategoria and self.categoria and self.subcategoria.categoria != self.categoria:
            raise ValidationError("La subcategoría no pertenece a la categoría seleccionada.")

class RegistroEvento(models.Model):
    STATUS_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('escaneado', 'Escaneado'),
    ]
    idRegistro = models.AutoField(primary_key=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='eventos_registrados')
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE, related_name='usuarios_registrados')
    fRegistro = models.DateTimeField()
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='pendiente'
    )
    fEscaneo = models.DateTimeField(null=True, blank=True)
    escaneado_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='registros_eventos_escaneados'
    )

    class Meta:
        unique_together = ('usuario', 'evento')

    def save(self, *args, **kwargs):
        if not self.pk and not self.fRegistro:
            self.fRegistro = ahora_mx()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.usuario.aNombre} registrado en {self.evento.aNombre}"

class ArchivoEvento(models.Model):
    evento = models.ForeignKey("Evento", on_delete=models.CASCADE, related_name="archivos")
    titulo = models.CharField(max_length=255)
    archivo = models.FileField(upload_to=archivo_evento_upload_path, validators=[validar_extension_archivo])
    fecha_subida = models.DateTimeField(auto_now_add=True)
    lActivo = models.BooleanField(default=True)

    def __str__(self):
        return self.titulo
