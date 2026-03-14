from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
import uuid
from django.conf import settings
from utils.fechas import ahora_mx

def generar_qr_string(usuario):
    return f"{uuid.uuid4().hex}"

class UsuarioManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("El email es obligatorio")
        email = self.normalize_email(email)
        extra_fields.setdefault('is_active', True)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('tipo_usuario', 'super_administrador')
        extra_fields.setdefault('verificado', True)
        return self.create_user(email, password, **extra_fields)

class Usuario(AbstractBaseUser, PermissionsMixin):
    TIPO_USUARIO_CHOICES = [
        ('cliente', 'Cliente'),
        ('administrador', 'Administrador'),
        ('super_administrador', 'Super Administrador'),
    ]

    idUsuario = models.AutoField(primary_key=True)
    aNombre = models.CharField(max_length=255)
    aApellido = models.CharField(max_length=255, null=True, blank=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)
    verificado = models.BooleanField(default=False)
    token_verificacion = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    email_verificado = models.DateTimeField(null=True, blank=True)
    tipo_usuario = models.CharField(
        max_length=50,
        choices=TIPO_USUARIO_CHOICES,
        default='cliente'
    )
    foto_perfil = models.ImageField(upload_to='usuarios/perfiles/', null=True, blank=True)
    aQr = models.CharField(max_length=255, unique=True, null=True, blank=True)
    aToken = models.CharField(max_length=255, unique=True, null=True, blank=True)
    aEmpresa = models.CharField(max_length=255, null=True, blank=True)
    aTelefono = models.CharField(max_length=20, null=True, blank=True)
    aWhatsapp = models.CharField(max_length=20, null=True, blank=True)
    aAnadic = models.CharField(
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
            ("Nacional", "Nacional"),
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
        null=True,
        blank=True
    )
    lActivo = models.BooleanField(default=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UsuarioManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['aNombre']

    def __str__(self):
        return self.aNombre

class PermisoPersonalizado(models.Model):
    usuario = models.ForeignKey("Usuario", on_delete=models.CASCADE, related_name="permisos_personalizados")
    categoria = models.CharField(max_length=50)
    accion = models.CharField(max_length=50)
    alcance = models.CharField(max_length=50, null=True, blank=True, choices=[
        ('estado', 'Estado ANADIC'),
        ('evento', 'Evento específico'),
        ('stand', 'Stand específico'),
        ('actividad', 'Actividad específica'),
    ])
    valor = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        unique_together = ('usuario', 'categoria', 'accion', 'alcance', 'valor')

    def __str__(self):
        return f"{self.usuario.email} | {self.categoria}.{self.accion} ({self.alcance}={self.valor})"

class ConfiguracionExportacion(models.Model):
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, related_name='configuracion_exportacion')
    activar_exportacion = models.BooleanField(default=False)
    intervalo_minutos = models.PositiveIntegerField(default=60)

    exportar_eventos = models.BooleanField(default=False)
    exportar_actividades = models.BooleanField(default=False)
    exportar_stands = models.BooleanField(default=False)

    def __str__(self):
        return f"Configuración exportación: {self.usuario.email}"

ESTADOS_MEXICO = [
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
]

class DireccionGuardada(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='direcciones_guardadas')
    dCalle = models.CharField(max_length=255, default="No especificado")
    dNumero = models.CharField(max_length=10, default="S/N")
    dColonia = models.CharField(max_length=255, default="No especificado")
    dCiudad = models.CharField(max_length=255, default="No especificado")
    dEstado = models.CharField(max_length=50, choices=ESTADOS_MEXICO, default="No especificado")
    dCP = models.CharField(max_length=10, default="00000")
    dLatitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    dLongitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    lPrivada = models.BooleanField(default=True, help_text="Si está activado, solo el usuario dueño puede usar esta dirección.")
    creado = models.DateTimeField()

    def save(self, *args, **kwargs):
        if not self.pk and not self.creado:
            self.creado = ahora_mx()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.dCalle} {self.dNumero}, {self.dColonia}, {self.dCiudad}, {self.dEstado}"

class OneSignalPlayer(models.Model):
    usuario = models.ForeignKey('Usuario', on_delete=models.CASCADE, related_name='players')
    player_id = models.CharField(max_length=255)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    dispositivo = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        unique_together = ('usuario', 'player_id')

    def __str__(self):
        return f"{self.usuario.email} - {self.player_id}"
