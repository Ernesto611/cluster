from django import forms
from .models import Stand, Producto, ArchivoStand
from usuarios.models import Usuario
from django.forms import DecimalField, BooleanField, NumberInput
from django.db.models import Q

CATEGORIAS_STAND = (
    'stands',
    'archivos_stand',
    'productos_stand',
    'registros_stands',
    'horarios_citas',
    'citas',
)

class StandForm(forms.ModelForm):
    representante_existente = forms.ModelChoiceField(
        queryset=Usuario.objects.filter(
            permisos_personalizados__categoria__in=CATEGORIAS_STAND
        ).distinct(),
        required=True,
        label="Representante",
        widget=forms.Select(attrs={'class': 'form-control'}),
    )

    nCostoCita = DecimalField(
        label="Costo de la cita",
        required=False,
        initial=0,
        widget=NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
    lPagoPresencialPermitido = BooleanField(
        label="¿Permitir pago presencial?",
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model = Stand
        fields = ['aNombre', 'aImagen', 'nNumeroStand', 'idEvento', 'aDescripcion', 'nCostoCita', 'lPagoPresencialPermitido']
        widgets = {
            'aNombre': forms.TextInput(attrs={'class': 'form-control'}),
            'aDescripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'aImagen': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'nNumeroStand': forms.NumberInput(attrs={'class': 'form-control'}),
            'idEvento': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        self.forzar_representante = kwargs.pop('forzar_representante', False)
        self.usuario_autenticado = kwargs.pop('usuario_autenticado', None)
        super().__init__(*args, **kwargs)

        if self.request and not self.forzar_representante:
            self.fields['representante_existente'].queryset = (
                Usuario.objects
                .filter(permisos_personalizados__categoria__in=CATEGORIAS_STAND)
                .distinct()
            )

        if self.instance and self.instance.pk:
            self.fields['representante_existente'].initial = self.instance.representante

        if self.forzar_representante and self.usuario_autenticado:
            self.fields['representante_existente'].queryset = Usuario.objects.filter(pk=self.usuario_autenticado.pk)
            self.fields['representante_existente'].initial = self.usuario_autenticado.pk
            self.fields['representante_existente'].widget = forms.HiddenInput()

    def clean(self):
        cleaned_data = super().clean()

        if not self.forzar_representante and not cleaned_data.get('representante_existente'):
            raise forms.ValidationError("Debes seleccionar un representante.")

        if self.forzar_representante and self.usuario_autenticado:
            cleaned_data['representante_existente'] = self.usuario_autenticado
        return cleaned_data

    def save(self, commit=True):
        stand = super().save(commit=False)

        if self.forzar_representante and self.usuario_autenticado:
            stand.representante = self.usuario_autenticado
        else:
            stand.representante = self.cleaned_data['representante_existente']
        if commit:
            stand.save()
        return stand

class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ['aNombre', 'aImagen', 'nPrecio']
        labels = {'aNombre': "Nombre", 'aImagen': "Imagen", 'nPrecio': "Precio"}

        widgets = {
            'aNombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del Producto'}),
            'aImagen': forms.FileInput(attrs={'class': 'form-control'}),
            'nPrecio': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Precio del Producto'}),
        }

class ArchivoStandForm(forms.ModelForm):
    class Meta:
        model = ArchivoStand
        fields = ['titulo', 'archivo']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-control'}),
            'archivo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }
