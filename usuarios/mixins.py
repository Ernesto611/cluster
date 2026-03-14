from django import forms
from .models import Usuario

class EmailUniqueValidationMixin:
    def clean_email(self):
        email = self.cleaned_data.get('email')
        qs = Usuario.objects.filter(email=email)

        if hasattr(self, 'instance') and getattr(self.instance, 'pk', None):
            if hasattr(self.instance, 'usuario'):
                qs = qs.exclude(pk=self.instance.usuario.pk)
            else:
                qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError("Ya existe un usuario con este correo electrónico.")

        return email
