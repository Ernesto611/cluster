from django.db import models
from eventos.models import Evento
from actividades.models import Actividad
from usuarios.models import Usuario
import uuid
from utils.fechas import ahora_mx

class Entrada(models.Model):
    idEntrada = models.AutoField(primary_key=True)
    idEvento = models.ForeignKey(Evento, on_delete=models.CASCADE, related_name='entradas')
    aNombre = models.CharField(max_length=255)
    nCosto = models.DecimalField(max_digits=10, decimal_places=2)
    nCantidad = models.PositiveIntegerField()
    nVendidas = models.PositiveIntegerField(default=0)
    lMultiple = models.BooleanField(default=False, help_text="Permite comprar más de una entrada en una sola compra.")
    lActivo = models.BooleanField(default=True)

    def __str__(self):
        return self.aNombre

class EntradaActividad(models.Model):
    idEntrada = models.ForeignKey(Entrada, on_delete=models.CASCADE, related_name='actividades_incluidas')
    idActividad = models.ForeignKey(Actividad, on_delete=models.CASCADE, related_name='entradas_incluidas')

    def __str__(self):
        return f"{self.idEntrada.aNombre} - {self.idActividad.aNombre}"

class CompraEntrada(models.Model):
    STATUS_PAGO = [
        ('pendiente', 'Pendiente'),
        ('pagado', 'Pagado'),
    ]

    METODOS_PAGO = [
        ('paypal', 'PayPal'),
        ('stripe', 'Tarjeta'),
        ('openpay', 'OpenPay'),
        ('efectivo', 'Efectivo'),
        ('gratuito_cuponado', 'Gratuito (Cupón)'),
    ]

    idCompra = models.AutoField(primary_key=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="compras")
    entrada = models.ForeignKey("Entrada", on_delete=models.CASCADE, related_name="compras")
    fecha_compra = models.DateTimeField()
    metodo_pago = models.CharField(max_length=18, choices=METODOS_PAGO)
    monto_pago = models.DecimalField(max_digits=10, decimal_places=2)
    status_pago = models.CharField(max_length=10, choices=STATUS_PAGO, default='pendiente')
    nCantidad = models.PositiveIntegerField(default=1)
    cupon = models.ForeignKey("Cupon", null=True, blank=True, on_delete=models.SET_NULL)

    referencia_pago = models.CharField(max_length=100, blank=True, null=True)
    comprobante_pago = models.ImageField(upload_to='compras/comprobantes/', null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.pk and not self.fecha_compra:
            self.fecha_compra = ahora_mx()
        if self.metodo_pago == 'efectivo' and not self.referencia_pago:
            self.referencia_pago = f"{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Compra {self.idCompra} - {self.entrada.aNombre} - {self.usuario.aNombre} - {self.status_pago}"

class Cupon(models.Model):
    TIPO_DESCUENTO = (
        ('porcentaje', 'Porcentaje'),
        ('cantidad', 'Cantidad fija'),
    )

    aCodigo = models.CharField(max_length=50, unique=True)
    eTipo = models.CharField(max_length=20, choices=TIPO_DESCUENTO)
    nValor = models.DecimalField(max_digits=10, decimal_places=2)
    nLimiteUso = models.PositiveIntegerField(null=True, blank=True)
    nUsados = models.PositiveIntegerField(default=0)
    entrada = models.ForeignKey('Entrada', on_delete=models.CASCADE, related_name='cupones')
    lAplicaTotal = models.BooleanField(default=False, help_text="¿El cupón se aplica al total (todas las entradas) o solo a una unidad?")
    lActivo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.aCodigo} ({self.get_eTipo_display()})"

    def esta_disponible(self):
        return self.lActivo and (self.nLimiteUso is None or self.nUsados < self.nLimiteUso)

class CodigoEntrada(models.Model):
    codigo = models.CharField(max_length=64, unique=True, default=uuid.uuid4)
    compra = models.ForeignKey(CompraEntrada, on_delete=models.CASCADE, related_name='codigos')
    activado_por = models.ForeignKey(Usuario, null=True, blank=True, on_delete=models.SET_NULL, related_name='codigos_usados')
    fecha_activacion = models.DateTimeField(null=True, blank=True)

    def esta_activado(self):
        return self.activado_por is not None

    def __str__(self):
        return f"Código {self.codigo} - {'Usado' if self.esta_activado() else 'Disponible'}"
