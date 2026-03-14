from django.db import models
from eventos.models import Evento
from usuarios.models import Usuario
from utils.fechas import ahora_mx

class TipoActividad(models.Model):
    idTipo = models.AutoField(primary_key=True)
    aNombre = models.CharField(max_length=255, unique=True)
    lActivo = models.BooleanField(default=True)

    def __str__(self):
        return self.aNombre

class Actividad(models.Model):
    idActividad = models.AutoField(primary_key=True)
    idEvento = models.ForeignKey(Evento, on_delete=models.CASCADE, related_name='actividades')
    aNombre = models.CharField(max_length=255)
    aDescripcion = models.TextField()
    idTipo = models.ForeignKey(TipoActividad, on_delete=models.SET_NULL, null=True, related_name='actividades')
    nCosto = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    nCapacidad = models.PositiveIntegerField()
    nLugaresDisponibles = models.PositiveIntegerField()
    fFechaHoraInicio = models.DateTimeField()
    fFechaHoraFin = models.DateTimeField()
    lAcompañantes = models.BooleanField(default=False)
    nAcompañantes = models.PositiveIntegerField(default=0)
    lActivo = models.BooleanField(default=True)
    lMismaDireccion = models.BooleanField(default=True)
    dDireccion = models.CharField(max_length=255, blank=True, null=True)
    dCalle = models.CharField(max_length=255, blank=True, null=True)
    dNumero = models.CharField(max_length=50, blank=True, null=True)
    dColonia = models.CharField(max_length=255, blank=True, null=True)
    dCP = models.CharField(max_length=10, blank=True, null=True)
    dCiudad = models.CharField(max_length=255, blank=True, null=True)
    dEstado = models.CharField(max_length=255, blank=True, null=True)
    dLatitud = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    dLongitud = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)

    def __str__(self):
        return f"{self.aNombre} - {self.idEvento.aNombre}"

class RegistroActividad(models.Model):
    STATUS_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('escaneado', 'Escaneado'),
    ]
    idRegistro = models.AutoField(primary_key=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='actividades_registradas')
    actividad = models.ForeignKey(Actividad, on_delete=models.CASCADE, related_name='usuarios_registrados')
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
        related_name='registros_actividades_escaneados'
    )

    class Meta:
        unique_together = ('usuario', 'actividad')

    def save(self, *args, **kwargs):
        if not self.pk and not self.fRegistro:
            self.fRegistro = ahora_mx()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.usuario.aNombre} registrado en {self.actividad.aNombre}"

class AcompañanteActividad(models.Model):
    idAcompaniante = models.AutoField(primary_key=True)
    registro = models.ForeignKey(RegistroActividad, on_delete=models.CASCADE, related_name='acompañantes_registrados')
    aNombre = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.aNombre} registrado como acompañante de {self.registro.usuario.aNombre}"

class CompraActividad(models.Model):
    STATUS_PAGO = [
        ('pendiente', 'Pendiente'),
        ('pagado', 'Pagado'),
    ]

    METODOS_PAGO = [
        ('paypal', 'PayPal'),
        ('stripe', 'Tarjeta'),
        ('openpay', 'OpenPay'),
    ]

    idCompra = models.AutoField(primary_key=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="compras_actividades")
    actividad = models.ForeignKey("Actividad", on_delete=models.CASCADE, related_name="compras_actividades")
    fecha_compra = models.DateTimeField()
    metodo_pago = models.CharField(max_length=10, choices=METODOS_PAGO)
    monto_pago = models.DecimalField(max_digits=10, decimal_places=2)
    status_pago = models.CharField(max_length=10, choices=STATUS_PAGO, default='pendiente')

    def save(self, *args, **kwargs):
        if not self.pk and not self.fecha_compra:
            self.fecha_compra = ahora_mx()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Compra {self.idCompra} - {self.actividad.aNombre} - {self.usuario.aNombre} - {self.status_pago}"
