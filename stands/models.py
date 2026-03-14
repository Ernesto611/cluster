from django.db import models
from eventos.models import Evento
import os
import uuid
from datetime import datetime
from usuarios.models import Usuario
from django.core.exceptions import ValidationError
from utils.fechas import ahora_mx

def archivo_stand_upload_path(instance, filename):
    ext = filename.split('.')[-1]
    new_filename = f"{uuid.uuid4().hex}.{ext}"
    return os.path.join("stands", "descargas", str(instance.stand.idStand), new_filename)

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

def renombrar_archivo(instance, filename):
    ext = filename.split('.')[-1]
    fecha_hora = datetime.now().strftime('%Y%m%d%H%M%S')
    nombre = f"{fecha_hora}-{uuid.uuid4().hex}.{ext}"
    return os.path.join('stands/imagenes/', nombre)

def renombrar_archivo_productos(instance, filename):
    ext = filename.split('.')[-1]
    fecha_hora = datetime.now().strftime('%Y%m%d%H%M%S')
    nombre = f"{fecha_hora}-{uuid.uuid4().hex}.{ext}"
    return os.path.join('stands/imagenes/productos/', nombre)

class Stand(models.Model):
    idStand = models.AutoField(primary_key=True)
    aNombre = models.CharField(max_length=255, null=True, blank=True)
    aDescripcion = models.TextField(null=True, blank=True)
    aImagen = models.ImageField(upload_to=renombrar_archivo, null=True, blank=True)
    nNumeroStand = models.PositiveIntegerField(null=True, blank=True)
    idEvento = models.ForeignKey(Evento, on_delete=models.CASCADE, related_name='stands')
    representante = models.ForeignKey( Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name="stands_representados")
    nCostoCita = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Costo de cada cita. Dejar en 0 si serán gratuitas.")
    lPagoPresencialPermitido = models.BooleanField(default=False, help_text="¿Se permite el pago presencial de las citas?")
    lActivo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.aNombre} - Stand {self.nNumeroStand} ({self.idEvento.aNombre})"

class Producto(models.Model):
    idProducto = models.AutoField(primary_key=True)
    aNombre = models.CharField(max_length=255)
    aImagen = models.ImageField(upload_to=renombrar_archivo_productos, null=True, blank=True)
    nPrecio = models.DecimalField(max_digits=10, decimal_places=2)
    idStand = models.ForeignKey(Stand, on_delete=models.CASCADE, related_name='productos')
    lActivo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.aNombre} - ${self.nPrecio}"

    def delete(self, *args, **kwargs):
        if self.aImagen:
            if os.path.isfile(self.aImagen.path):
                os.remove(self.aImagen.path)
        super().delete(*args, **kwargs)

class RegistroStand(models.Model):
    STATUS_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('escaneado', 'Escaneado'),
    ]
    idRegistro = models.AutoField(primary_key=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='stands_registradas')
    stand = models.ForeignKey(Stand, on_delete=models.CASCADE, related_name='usuarios_registrados')
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
        related_name='registros_stands_escaneados'
    )

    class Meta:
        unique_together = ('usuario', 'stand')

    def save(self, *args, **kwargs):
        if not self.pk and not self.fRegistro:
            self.fRegistro = ahora_mx()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.usuario.aNombre} registrado en {self.stand.aNombre}"

class CitaStand(models.Model):
    STATUS_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('aceptada', 'Aceptada'),
        ('rechazada', 'Rechazada'),
        ('cancelada', 'Cancelada'),
        ('completada', 'Completada'),
    ]

    idCita = models.AutoField(primary_key=True)
    idStand = models.ForeignKey(Stand, on_delete=models.CASCADE, related_name="citas")
    idUsuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="citas")
    aStatus = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendiente')
    fFechaHora = models.DateTimeField()
    aMensaje = models.TextField(null=True, blank=True)
    aNotas = models.TextField(null=True, blank=True)
    STATUS_PAGO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('pagado', 'Pagado'),
    ]

    metodo_pago = models.CharField(max_length=20, null=True, blank=True)
    monto_pago = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status_pago = models.CharField(max_length=20, choices=STATUS_PAGO_CHOICES, default='pendiente')

    def __str__(self):
        representante = self.idStand.representante.aNombre if self.idStand.representante else "Sin representante"
        return f"Cita {self.idCita} - {self.idUsuario.aNombre} con {representante} - {self.get_aStatus_display()}"

class HorarioCita(models.Model):
    idHorario = models.AutoField(primary_key=True)
    idStand = models.ForeignKey(Stand, on_delete=models.CASCADE, related_name="horarios")
    fFechaHora = models.DateTimeField()

    class Meta:
        unique_together = ('idStand', 'fFechaHora')
        ordering = ['fFechaHora']

    def __str__(self):
        return f"{self.idStand.aNombre} - {self.fFechaHora.strftime('%d/%m/%Y %H:%M')}"

class ArchivoStand(models.Model):
    stand = models.ForeignKey("Stand", on_delete=models.CASCADE, related_name="archivos")
    titulo = models.CharField(max_length=255)
    archivo = models.FileField(upload_to=archivo_stand_upload_path, validators=[validar_extension_archivo])
    lActivo = models.BooleanField(default=True)
    fecha_subida = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.titulo
