from django import forms
from .models import Entrada, EntradaActividad, Cupon
from actividades.models import Actividad

class EntradaForm(forms.ModelForm):
    class Meta:
        model = Entrada
        fields = [
            'idEvento',
            'aNombre',
            'nCosto',
            'nCantidad',
            'lMultiple'
        ]

        widgets = {
            'idEvento': forms.Select(attrs={
                'class': 'form-control',
                'id': 'entrada-evento-input',
                'required': True,
            }),
            'aNombre': forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'entrada-name-input',
                'placeholder': 'Nombre de la entrada',
                'required': True,
            }),
            'nCosto': forms.NumberInput(attrs={
                'class': 'form-control',
                'id': 'entrada-costo-input',
                'placeholder': 'Costo de la entrada',
                'required': True,
            }),
            'lMultiple': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'id': 'entrada-multiple-checkbox',
            }),
            'nCantidad': forms.NumberInput(attrs={
                'class': 'form-control',
                'id': 'entrada-cantidad-input',
                'placeholder': 'Cantidad de entradas disponibles',
                'required': True,
            }),
        }

    incluir_actividades = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'incluir-actividades-checkbox',
        }),
        label='¿Incluir actividades?',
    )

    actividades = forms.ModelMultipleChoiceField(
        queryset=Actividad.objects.all(),
        widget=forms.SelectMultiple(attrs={
            'class': 'form-control',
            'id': 'entrada-actividades-input',
            'disabled': True,
        }),
        required=False,
    )

    def save(self, commit=True):
        entrada = super().save(commit=commit)
        if commit:
            if self.cleaned_data.get('incluir_actividades', False):
                actividades_seleccionadas = self.cleaned_data.get('actividades', [])
                for actividad in actividades_seleccionadas:
                    EntradaActividad.objects.create(idEntrada=entrada, idActividad=actividad)
        return entrada

class CuponForm(forms.ModelForm):
    indicador = forms.CharField(
        max_length=4,
        required=False,
        label="Indicador (opcional)",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej. VIP',
            'id': 'cupon-indicador-input'
        })
    )

    class Meta:
        model = Cupon
        fields = ['eTipo', 'nValor', 'nLimiteUso', 'lAplicaTotal']
        widgets = {
            'eTipo': forms.Select(attrs={
                'class': 'form-control',
                'id': 'cupon-tipo-input',
                'required': True,
            }),
            'nValor': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej. 10.00',
                'id': 'cupon-valor-input',
                'required': True,
            }),
            'nLimiteUso': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Dejar vacío si es ilimitado',
                'id': 'cupon-limite-input',
            }),
            'lAplicaTotal': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'id': 'cupon-aplicatotal-checkbox',
            }),
        }
