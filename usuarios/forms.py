from django import forms
from .models import Usuario, ConfiguracionExportacion
from eventos.models import Evento
from actividades.models import Actividad
from stands.models import Stand
from .mixins import EmailUniqueValidationMixin

class AdministradorForm(forms.ModelForm, EmailUniqueValidationMixin):
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Contraseña',
            'autocomplete': 'new-password'
        })
    )

    class Meta:
        model = Usuario
        fields = ['aNombre', 'aApellido', 'email', 'password', 'aAnadic']
        widgets = {
            'aNombre': forms.TextInput(attrs={'class': 'form-control'}),
            'aApellido': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'aAnadic': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        if self.request:
            user = self.request.user
            if user.tipo_usuario != 'super_administrador' and user.aAnadic != 'Nacional':
                self.fields['aAnadic'].disabled = True
                self.fields['aAnadic'].initial = user.aAnadic

    def save(self, commit=True):
        usuario = super().save(commit=False)
        password = self.cleaned_data.get('password')
        if password:
            usuario.set_password(password)

        usuario.tipo_usuario = 'administrador'

        if self.request:
            user = self.request.user
            if user.tipo_usuario != 'super_administrador' and user.aAnadic.nombre != 'Nacional':
                usuario.aAnadic = user.aAnadic

        if commit:
            usuario.save()

        return usuario

class GestorForm(forms.ModelForm, EmailUniqueValidationMixin):
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Contraseña',
            'autocomplete': 'new-password'
        })
    )

    class Meta:
        model = Usuario
        fields = ['aNombre', 'aApellido', 'email', 'password', 'aAnadic']
        widgets = {
            'aNombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre'}),
            'aApellido': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apellidos'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Correo electrónico', 'autocomplete': 'new-email'}),
            'aAnadic': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        if self.request and self.request.user.tipo_usuario != 'super_administrador':
            self.fields.pop('aAnadic')

    def save(self, commit=True):
        usuario = super().save(commit=False)

        password = self.cleaned_data.get('password')
        if password:
            usuario.set_password(password)

        usuario.tipo_usuario = 'gestor'
        usuario.verificado = True

        if 'aAnadic' not in self.cleaned_data:
            usuario.aAnadic = self.request.user.aAnadic

        if commit:
            usuario.save()

        return usuario

class ConfiguracionExportacionForm(forms.ModelForm):
    class Meta:
        model = ConfiguracionExportacion
        fields = [
            'activar_exportacion',
            'intervalo_minutos',
            'exportar_eventos',
            'exportar_actividades',
            'exportar_stands',
        ]
        labels = {
            'activar_exportacion': 'Activar descargas automáticas',
            'intervalo_minutos': 'Intervalo (minutos)',
            'exportar_eventos': 'Registros de eventos',
            'exportar_actividades': 'Registros de actividades',
            'exportar_stands': 'Registros de stands',
        }
