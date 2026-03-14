from django import forms
from django.forms import ModelForm
from .models import ChatbotConfig, ChatbotDocumento
from django.core.exceptions import ValidationError
import os

class ChatbotConfigForm(ModelForm):
    class Meta:
        model = ChatbotConfig
        fields = ['nombre', 'seccion_fija', 'seccion_editable']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre de la configuración'
            }),
            'seccion_fija': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 10,
                'placeholder': 'Reglas base del chatbot (no elimines las esenciales)...'
            }),
            'seccion_editable': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 10,
                'placeholder': 'Información editable del chatbot...'
            })
        }
        labels = {
            'nombre': 'Nombre de la Configuración',
            'seccion_fija': 'Sección Fija (Advertencia: no eliminar reglas críticas)',
            'seccion_editable': 'Información Editable'
        }

class ChatbotDocumentoForm(forms.ModelForm):
    class Meta:
        model = ChatbotDocumento
        fields = ['nombre', 'archivo']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre descriptivo del documento'
            }),
            'archivo': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.docx,.doc,.pptx,.xlsx,.jpg,.jpeg,.png,.webp'
            })
        }
        labels = {
            'nombre': 'Nombre del documento',
            'archivo': 'Archivo'
        }
        help_texts = {
            'archivo': 'Formatos permitidos: PDF, DOCX, DOC, PPTX, XLSX, JPG, JPEG, PNG, WEBP (máximo 10MB)'
        }

    def clean_archivo(self):
        archivo = self.cleaned_data.get('archivo')

        if archivo:

            if archivo.size > 10 * 1024 * 1024:
                raise ValidationError('El archivo no puede superar los 10MB.')

            nombre_archivo = archivo.name.lower()
            extensiones_permitidas = ['.pdf', '.docx', '.doc', '.pptx', '.xlsx', '.jpg', '.jpeg', '.png', '.webp']

            if not any(nombre_archivo.endswith(ext) for ext in extensiones_permitidas):
                raise ValidationError('Solo se permiten archivos PDF, DOCX o DOC.')

            if archivo.size == 0:
                raise ValidationError('El archivo está vacío.')

        return archivo

    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre')

        if nombre:

            nombre = nombre.strip()

            if len(nombre) < 3:
                raise ValidationError('El nombre debe tener al menos 3 caracteres.')

            if not nombre:
                raise ValidationError('El nombre no puede estar vacío.')

        return nombre

    def save(self, commit=True):
        instance = super().save(commit=False)

        if not hasattr(instance, 'activo') or instance.activo is None:
            instance.activo = True

        if commit:
            instance.save()

        return instance
