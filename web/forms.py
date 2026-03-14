from django import forms
from .models import BannerPrincipal, ArchivoPagina, DatosPagoEfectivoConfiguracion
from usuarios.models import Usuario
from django.core.exceptions import ValidationError
from PIL import Image
from django_recaptcha.fields import ReCaptchaField

class PerfilForm(forms.ModelForm):
    foto_perfil = forms.ImageField(required=False, widget=forms.FileInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(disabled=True, required=False, widget=forms.EmailInput(attrs={'class': 'form-control'}))

    aTelefono = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Número de teléfono'})
    )
    aWhatsapp = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Número de WhatsApp'})
    )
    usar_mismo_numero = forms.BooleanField(
        required=False,
        label="Usar el mismo número de teléfono para WhatsApp"
    )

    class Meta:
        model = Usuario
        fields = ['aNombre', 'aApellido', 'email', 'foto_perfil', 'aEmpresa', 'aTelefono', 'aWhatsapp']
        widgets = {
            'aNombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese su nombre'}),
            'aApellido': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese sus apellidos'}),
            'aEmpresa': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese el nombre de la empresa'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("usar_mismo_numero"):
            cleaned_data["aWhatsapp"] = cleaned_data.get("aTelefono")
        return cleaned_data

BLOCKED_DOMAINS = [
    'br.ru', 'mail.ru', 'list.ru', 'inbox.ru', 'bk.ru',
    'yandex.ru', 'rambler.ru', 'yahoo.ru'
]

class RegistroNoSocioForm(forms.ModelForm):
    email_confirm = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Confirma tu correo electrónico'}),
        required=True,
        label="Confirmar correo"
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese su contraseña'}),
        required=True,
        label="Contraseña"
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirme su contraseña'}),
        required=True,
        label="Confirmar contraseña"
    )
    aTelefono = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Número de teléfono'})
    )
    aWhatsapp = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Número de WhatsApp'})
    )
    usar_mismo_numero = forms.BooleanField(
        required=False,
        label="Usar el mismo número de teléfono para WhatsApp"
    )
    captcha = ReCaptchaField()
    class Meta:
        model = Usuario
        fields = ['aNombre', 'aApellido', 'email', 'password', 'aEmpresa', 'aTelefono', 'aWhatsapp']
        widgets = {
            'aNombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese su nombre'}),
            'aApellido': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese su o sus apellidos'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese su correo electrónico'}),
            'aEmpresa': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese el nombre de la empresa'}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')

        if not email:
            raise forms.ValidationError("El email es requerido.")

        try:
            domain = email.split('@')[1].lower()
        except IndexError:
            raise forms.ValidationError("Formato de email inválido.")

        if domain in BLOCKED_DOMAINS:
            raise forms.ValidationError(
                "Este dominio de email no está permitido para registro."
            )

        if Usuario.objects.filter(email=email).exists():
            raise forms.ValidationError("Este correo ya está registrado.")

        return email

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("email")
        email_confirm = cleaned_data.get("email_confirm")
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")
        usar_mismo = cleaned_data.get("usar_mismo_numero")

        if email and email_confirm and email != email_confirm:
            self.add_error("email_confirm", "Los correos no coinciden.")

        if password and password_confirm and password != password_confirm:
            self.add_error("password_confirm", "Las contraseñas no coinciden.")

        if usar_mismo:
            cleaned_data["aWhatsapp"] = cleaned_data.get("aTelefono")

        return cleaned_data

class ReenviarVerificacionForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese su correo electrónico'}),
        label="Correo Electrónico",
        required=True
    )

class BannerPrincipalForm(forms.ModelForm):
    class Meta:
        model = BannerPrincipal
        fields = ['titulo', 'url']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Título del banner', 'required': True}),
            'url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'Ejemplo: https://www.misitio.com'}),
        }

class ArchivoPaginaForm(forms.ModelForm):
    class Meta:
        model = ArchivoPagina
        fields = ['titulo', 'archivo']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-control'}),
            'archivo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

class DatosPagoEfectivoForm(forms.ModelForm):
    class Meta:
        model = DatosPagoEfectivoConfiguracion
        fields = [
            'aNombreBanco',
            'aNombreBeneficiario',
            'aNumeroCuenta',
            'aClabe',
            'lActivo',
        ]
        widgets = {
            'aNombreBanco': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre del banco'
            }),
            'aNombreBeneficiario': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre del beneficiario'
            }),
            'aNumeroCuenta': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número de cuenta'
            }),
            'aClabe': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'CLABE interbancaria'
            }),
            'lActivo': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
