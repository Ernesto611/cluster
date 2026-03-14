from django import forms
from .models import Agenda, AgendaActividades
from actividades.models import Actividad

class AgendaForm(forms.ModelForm):
    class Meta:
        model = Agenda
        fields = ['idEvento', 'aNombre', 'lVisible', 'lActivo']
        widgets = {
            'idEvento': forms.Select(attrs={'class': 'form-control'}),
            'aNombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de la agenda'}),
            'lVisible': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'lActivo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class AgendaActividadesForm(forms.Form):
    actividades = forms.ModelMultipleChoiceField(
        queryset=Actividad.objects.filter(lActivo=True),
        widget=forms.SelectMultiple(attrs={'class': 'form-control'}),
        label="Actividades"
    )
