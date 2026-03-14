from django import forms
from usuarios.models import Usuario
from .models import Patrocinador
from stands.models import Stand
from eventos.models import Evento

class PatrocinadorForm(forms.ModelForm):
    tiene_stand = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label="¿Tendrá stand?"
    )
    whatsapp_es_mismo = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label="Usar el mismo número de teléfono"
    )

    class Meta:
        model = Patrocinador
        fields = [
            'aNombre', 'aBiografia', 'aTelefono', 'aWhatsapp', 'aEmail', 'aFacebook',
            'aInstagram', 'aTwitter', 'aSitioWeb', 'aFoto', 'idEvento'
        ]
        labels = {
            'aBiografia': "Biografía",
            'aTelefono': "Teléfono",
            'aWhatsapp': "WhatsApp",
            'aFacebook': "Facebook",
            'aInstagram': "Instagram",
            'aTwitter': "Twitter",
            'aSitioWeb': "Sitio Web",
            'aFoto': "Foto",
            'idEvento': "Evento",
            'aNombre': "Nombre",
            'aEmail': "Correo electrónico"
        }
        widgets = {
            'aNombre': forms.TextInput(attrs={'class': 'form-control'}),
            'aBiografia': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'aTelefono': forms.TextInput(attrs={'class': 'form-control'}),
            'aWhatsapp': forms.TextInput(attrs={'class': 'form-control'}),
            'aEmail': forms.EmailInput(attrs={'class': 'form-control'}),
            'aFacebook': forms.TextInput(attrs={'class': 'form-control'}),
            'aInstagram': forms.TextInput(attrs={'class': 'form-control'}),
            'aTwitter': forms.TextInput(attrs={'class': 'form-control'}),
            'aSitioWeb': forms.URLInput(attrs={'class': 'form-control'}),
            'aFoto': forms.FileInput(attrs={'class': 'form-control'}),
            'idEvento': forms.Select(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('whatsapp_es_mismo'):
            cleaned_data['aWhatsapp'] = cleaned_data.get('aTelefono')
        return cleaned_data

    def __init__(self, *args, **kwargs):
        eventos = kwargs.pop('eventos', None)
        super().__init__(*args, **kwargs)
        if eventos is not None:
            self.fields['idEvento'].queryset = eventos
