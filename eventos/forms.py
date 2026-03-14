from django import forms
from .models import Evento, ArchivoEvento, CategoriaEvento, SubcategoriaEvento
from PIL import Image

class CategoriaEstiloForm(forms.ModelForm):
    class Meta:
        model = CategoriaEvento
        fields = ["estilo_detalle_evento", "logo"]
        widgets = {
            "estilo_detalle_evento": forms.RadioSelect(
                choices=[('1', 'Estilo 1'), ('2', 'Estilo 2')]
            ),
        }

    def clean_logo(self):
        f = self.cleaned_data.get("logo")
        if not f:
            return f
        try:
            img = Image.open(f)
            w, h = img.size
            if (w, h) != (178, 25):
                raise forms.ValidationError(
                    "El logo debe ser exactamente 178x25 px. Usa el recorte antes de guardar."
                )
        except Exception:
            raise forms.ValidationError("No se pudo leer la imagen del logo.")
        return f

class EventoForm(forms.ModelForm):
    class Meta:
        model = Evento
        fields = [
            'aNombre',
            'aDescripcion',
            'fFechaInicio',
            'fFechaFin',
            'dCalle',
            'dNumero',
            'dColonia',
            'dCiudad',
            'dEstado',
            'dCP',
            'dLatitud',
            'dLongitud',
            'lGratuito',
            'aImagen',
            'lAgendaVisible',
            'categoria',
            'subcategoria',
        ]

        widgets = {
            'aNombre': forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'event-name-input',
                'placeholder': 'Nombre del evento',
                'required': True
            }),
            'aDescripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'id': 'event-description-input',
                'placeholder': 'Descripción del evento',
                'rows': 4,
                'required': True
            }),
            'fFechaInicio': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'fFechaFin': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'dCalle': forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'event-street-input',
                'placeholder': 'Calle',
                'required': True
            }),
            'dNumero': forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'event-number-input',
                'placeholder': 'Número',
                'required': False
            }),
            'dColonia': forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'event-neighborhood-input',
                'placeholder': 'Colonia',
                'required': True
            }),
            'dCiudad': forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'event-city-input',
                'placeholder': 'Ciudad',
                'required': True
            }),
            'dEstado': forms.Select(attrs={
                'class': 'form-control',
                'id': 'event-state-input',
            }, choices=[
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
            ]),
            'dCP': forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'event-zipcode-input',
                'placeholder': 'Código Postal',
                'required': True
            }),
            'dLatitud': forms.NumberInput(attrs={
                'class': 'form-control',
                'id': 'event-latitude-input',
                'readonly': True
            }),
            'dLongitud': forms.NumberInput(attrs={
                'class': 'form-control',
                'id': 'event-longitude-input',
                'readonly': True
            }),
            'lGratuito': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'id': 'event-free-checkbox',
            }),
            'aImagen': forms.FileInput(attrs={
                'class': 'form-control',
                'id': 'event-image-input',
            }),
            'lAgendaVisible': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'id': 'event-agenda-visible-checkbox',
            }),
            'categoria': forms.Select(attrs={
                'class': 'form-control',
                'id': 'event-category-select',
                'required': True,
            }),
            'subcategoria': forms.Select(attrs={
                'class': 'form-control',
                'id': 'event-subcategory-select',
                'disabled': True
            }),
        }

    def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.fields['categoria'].queryset = CategoriaEvento.objects.filter(lActivo=True)
            self.fields['categoria'].required = True
            self.fields['categoria'].label = "Categoría"

            self.fields['subcategoria'].label = "Subcategoría"
            self.fields['subcategoria'].required = True

            if self.instance and self.instance.pk:
                categoria = self.instance.categoria
                if categoria:
                    self.fields['subcategoria'].queryset = SubcategoriaEvento.objects.filter(categoria=categoria, lActivo=True)
                else:
                    self.fields['subcategoria'].queryset = SubcategoriaEvento.objects.all()
                if self.instance.fFechaInicio:
                    self.initial['fFechaInicio'] = self.instance.fFechaInicio.strftime('%Y-%m-%dT%H:%M')
                if self.instance.fFechaFin:
                    self.initial['fFechaFin'] = self.instance.fFechaFin.strftime('%Y-%m-%dT%H:%M')
            else:
                self.fields['subcategoria'].queryset = SubcategoriaEvento.objects.all()
            if self.instance and self.instance.pk:
                if self.instance.fFechaInicio:
                    self.initial['fFechaInicio'] = self.instance.fFechaInicio.strftime('%Y-%m-%dT%H:%M')
                if self.instance.fFechaFin:
                    self.initial['fFechaFin'] = self.instance.fFechaFin.strftime('%Y-%m-%dT%H:%M')

    def clean_aImagen(self):
        imagen = self.cleaned_data.get('aImagen')
        if not imagen:
            raise forms.ValidationError("La imagen del evento es obligatoria.")
        return imagen

    def clean(self):
        cleaned_data = super().clean()
        inicio = cleaned_data.get('fFechaInicio')
        fin = cleaned_data.get('fFechaFin')

        if inicio and fin and fin <= inicio:
            self.add_error('fFechaFin', "La fecha de fin debe ser posterior a la fecha de inicio.")

class ArchivoEventoForm(forms.ModelForm):
    class Meta:
        model = ArchivoEvento
        fields = ['titulo', 'archivo']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-control'}),
            'archivo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

class CategoriaEventoForm(forms.ModelForm):
    class Meta:
        model = CategoriaEvento
        fields = ['aNombre', 'lActivo']
        widgets = {
            'aNombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre de la categoría'
            }),
            'lActivo': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

class SubcategoriaEventoForm(forms.ModelForm):
    class Meta:
        model = SubcategoriaEvento
        fields = ['aNombre', 'categoria', 'lActivo']
        widgets = {
            'aNombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre de la subcategoría'
            }),
            'categoria': forms.Select(attrs={
                'class': 'form-select'
            }),
            'lActivo': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
