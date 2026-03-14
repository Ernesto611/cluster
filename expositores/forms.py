from django import forms
from .models import Expositor, ArchivoExpositor

class ExpositorForm(forms.ModelForm):
    whatsapp_es_mismo = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label="Usar el mismo número de teléfono"
    )

    class Meta:
        model = Expositor
        fields = [
            'aNombre', 'aBiografia', 'aTelefono', 'aWhatsapp', 'aEmail',
            'aFacebook', 'aInstagram', 'aTwitter', 'aSitioWeb', 'aFoto'
        ]
        widgets = {
            'aNombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre completo'}),
            'aBiografia': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Escribe una breve biografía'}),
            'aTelefono': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ejemplo: +52 123 456 7890'}),
            'aWhatsapp': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ejemplo: +52 123 456 7890'}),
            'aEmail': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Correo electrónico'}),
            'aFacebook': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tu usuario de Facebook'}),
            'aInstagram': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tu usuario de Instagram'}),
            'aTwitter': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tu usuario de Twitter'}),
            'aSitioWeb': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'Ejemplo: https://www.miweb.com'}),
            'aFoto': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("whatsapp_es_mismo"):
            cleaned_data['aWhatsapp'] = cleaned_data.get('aTelefono')
        return cleaned_data

class ArchivoExpositorForm(forms.ModelForm):
    class Meta:
        model = ArchivoExpositor
        fields = ['titulo', 'archivo']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-control'}),
            'archivo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }
