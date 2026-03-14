from django import forms
from .models import Actividad, TipoActividad
from eventos.models import Evento
from django.utils import timezone
import pytz

class ActividadForm(forms.ModelForm):
    class Meta:
        model = Actividad
        fields = [
            'idEvento',
            'aNombre',
            'aDescripcion',
            'idTipo',
            'nCosto',
            'nCapacidad',
            'fFechaHoraInicio',
            'fFechaHoraFin',
            'lAcompañantes',
            'nAcompañantes',
            'lActivo',
            'lMismaDireccion',
            'dDireccion',
            'dCalle',
            'dNumero',
            'dColonia',
            'dCP',
            'dCiudad',
            'dEstado',
            'dLatitud',
            'dLongitud',
        ]
        widgets = {
            'idEvento': forms.Select(attrs={'class': 'form-control'}),
            'aNombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de la actividad'}),
            'aDescripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Descripción de la actividad'}),
            'idTipo': forms.Select(attrs={'class': 'form-control'}),
            'nCosto': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Costo de la actividad (0 si es gratuita)', 'step': 'any'}),
            'nCapacidad': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Capacidad máxima'}),
            'fFechaHoraInicio': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'fFechaHoraFin': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'lAcompañantes': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'nAcompañantes': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Cantidad máxima de acompañantes'}),
            'lActivo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'lMismaDireccion': forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'same-location-checkbox'}),
            'dDireccion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Dirección completa'}),
            'dCalle': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Calle'}),
            'dNumero': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Número'}),
            'dColonia': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Colonia'}),
            'dCP': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Código Postal'}),
            'dCiudad': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ciudad'}),
            'dEstado': forms.Select(attrs={'class': 'form-control'}, choices=[
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
            'dLatitud': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Latitud', 'readonly': True}),
            'dLongitud': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Longitud', 'readonly': True}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            if self.instance.fFechaHoraInicio:
                self.initial['fFechaHoraInicio'] = self.instance.fFechaHoraInicio.strftime('%Y-%m-%dT%H:%M')
            if self.instance.fFechaHoraFin:
                self.initial['fFechaHoraFin'] = self.instance.fFechaHoraFin.strftime('%Y-%m-%dT%H:%M')

    def clean(self):
        cleaned_data = super().clean()
        fFechaHoraInicio = cleaned_data.get('fFechaHoraInicio')
        fFechaHoraFin = cleaned_data.get('fFechaHoraFin')
        evento = cleaned_data.get('idEvento')

        if fFechaHoraInicio and fFechaHoraFin and fFechaHoraInicio >= fFechaHoraFin:
            self.add_error('fFechaHoraFin', 'La fecha y hora de fin debe ser posterior a la de inicio.')

        if evento and fFechaHoraInicio and fFechaHoraFin:
            if fFechaHoraInicio < evento.fFechaInicio or fFechaHoraFin > evento.fFechaFin:
                raise forms.ValidationError(
                    'Las fechas de la actividad deben estar dentro del rango de fechas del evento: '
                    f'{evento.fFechaInicio.strftime("%d/%m/%Y %H:%M")} - {evento.fFechaFin.strftime("%d/%m/%Y %H:%M")}'
                )

        return cleaned_data

class TipoActividadForm(forms.ModelForm):
    class Meta:
        model = TipoActividad
        fields = ['aNombre', 'lActivo']
        widgets = {
            'aNombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre del tipo de actividad'
            }),
            'lActivo': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
