from django.db import models
from datetime import datetime
import uuid
import os
from utils.fechas import ahora_mx

def renombrar_archivo_notificacion(instance, filename):

    ext = filename.split('.')[-1]
    fecha_hora = datetime.now().strftime('%Y%m%d%H%M%S')
    nombre = f"{fecha_hora}-{uuid.uuid4().hex}.{ext}"
    return os.path.join('notificaciones/imagenes/', nombre)

def renombrar_archivo_historial(instance, filename):

    ext = filename.split('.')[-1]
    fecha_hora = datetime.now().strftime('%Y%m%d%H%M%S')
    nombre = f"{fecha_hora}-{uuid.uuid4().hex}.{ext}"
    return os.path.join('notificaciones/historial/imagenes/', nombre)

class Notificacion(models.Model):

    ESTADO_CHOICES = [
        ('borrador', 'Borrador'),
        ('enviada', 'Enviada'),
        ('programada', 'Programada'),
    ]

    titulo = models.CharField(max_length=200)
    mensaje = models.TextField()
    imagen = models.ImageField(
        upload_to=renombrar_archivo_notificacion,
        null=True,
        blank=True
    )

    fecha_programada = models.DateTimeField(null=True, blank=True)

    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='borrador')

    datos_adicionales = models.JSONField(default=dict, blank=True)

    creado_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.CASCADE,
        related_name='notificaciones_creadas'
    )
    fecha_creacion = models.DateTimeField(default=ahora_mx)
    fecha_modificacion = models.DateTimeField(default=ahora_mx)

    class Meta:
        ordering = ['-fecha_creacion']
        verbose_name = 'Notificación'
        verbose_name_plural = 'Notificaciones'

    def save(self, *args, **kwargs):

        self.fecha_modificacion = ahora_mx()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.usuario.email} - {self.titulo_original} - {self.fecha_envio}"

    def __str__(self):
        return f"{self.titulo} - {self.estado}"

class HistorialNotificacionImagen(models.Model):

    notificacion = models.ForeignKey(
        'Notificacion',
        on_delete=models.CASCADE,
        related_name='imagenes_historial'
    )
    imagen = models.ImageField(
        upload_to=renombrar_archivo_historial,
        null=True,
        blank=True
    )
    fecha_envio = models.DateTimeField()

    hash_imagen = models.CharField(max_length=64, null=True, blank=True)

    class Meta:
        verbose_name = 'Imagen de Historial'
        verbose_name_plural = 'Imágenes de Historial'
        unique_together = ('notificacion', 'fecha_envio')

    def __str__(self):
        return f"Imagen {self.notificacion.titulo} - {self.fecha_envio}"

class HistorialNotificacion(models.Model):

    ESTADO_ENTREGA_CHOICES = [
        ('entregada', 'Entregada'),
        ('vista', 'Vista'),
    ]

    usuario = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.CASCADE,
        related_name='historial_notificaciones'
    )

    titulo_original = models.CharField(max_length=200)
    mensaje_original = models.TextField()
    datos_adicionales_original = models.JSONField(default=dict, blank=True)

    imagen_historial = models.ForeignKey(
        'HistorialNotificacionImagen',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='historiales'
    )

    notificacion_referencia = models.ForeignKey(
        'Notificacion',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='historial_envios'
    )

    player_id = models.CharField(max_length=255)
    fecha_envio = models.DateTimeField()
    fecha_vista = models.DateTimeField(null=True, blank=True)

    estado_entrega = models.CharField(
        max_length=20,
        choices=ESTADO_ENTREGA_CHOICES,
        default='entregada'
    )

    fecha_creacion = models.DateTimeField(default=ahora_mx)
    fecha_modificacion = models.DateTimeField(default=ahora_mx)

    class Meta:
        ordering = ['-fecha_envio']
        verbose_name = 'Historial de Notificación'
        verbose_name_plural = 'Historial de Notificaciones'
        indexes = [
            models.Index(fields=['usuario', '-fecha_envio']),
            models.Index(fields=['notificacion_referencia']),
            models.Index(fields=['fecha_envio']),
        ]

    def save(self, *args, **kwargs):

        self.fecha_modificacion = ahora_mx()
        super().save(*args, **kwargs)

    def marcar_como_vista(self):

        if self.estado_entrega == 'entregada':
            self.estado_entrega = 'vista'
            self.fecha_vista = ahora_mx()
            self.save()

    @property
    def imagen_url(self):

        if self.imagen_historial and self.imagen_historial.imagen:
            return self.imagen_historial.imagen.url
        return None
