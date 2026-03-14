from django.db import models
from eventos.models import Evento
from utils.fechas import ahora_mx

class Aportador(models.Model):
    idAportador = models.AutoField(primary_key=True)
    aNombre = models.CharField(max_length=255)
    aEmail = models.EmailField(max_length=255)
    lActivo = models.BooleanField(default=True)

    def __str__(self):
        return self.aNombre

class Aportacion(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente de pago'),
        ('pagada', 'Pagada')
    ]

    METODO_PAGO_CHOICES = [
        ('efectivo', 'Efectivo'),
        ('paypal', 'PayPal'),
        ('stripe', 'Tarjeta'),
    ]

    idAportacion = models.AutoField(primary_key=True)
    aNombre = models.CharField(max_length=255)
    aDescripcion = models.TextField()
    eEstado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='pendiente')
    idEvento = models.ForeignKey(Evento, on_delete=models.CASCADE, related_name='aportaciones')
    idAportador = models.ForeignKey(Aportador, on_delete=models.CASCADE, related_name='aportaciones')
    fCreacion = models.DateTimeField(auto_now_add=True)
    fModificacion = models.DateTimeField(auto_now=True)
    fPago = models.DateTimeField(null=True, blank=True)
    lActivo = models.BooleanField(default=True)
    referencia_pago = models.CharField(max_length=100, blank=True, null=True)
    metodo_pago = models.CharField(max_length=20, choices=METODO_PAGO_CHOICES, blank=True, null=True)
    monto_pago = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.aNombre} - {self.idAportador.aNombre} - {self.get_eEstado_display()}"

    def marcar_como_pagada(self):
        self.eEstado = 'pagada'
        self.fPago = ahora_mx()
        self.save()
