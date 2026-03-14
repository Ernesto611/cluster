import os
from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import Evento

@receiver(pre_save, sender=Evento)
def eliminar_imagen_antigua(sender, instance, **kwargs):
    if not instance.pk:
        return

    try:
        evento_antiguo = sender.objects.get(pk=instance.pk)
        if evento_antiguo.aImagen and evento_antiguo.aImagen != instance.aImagen:

            if os.path.isfile(evento_antiguo.aImagen.path):
                os.remove(evento_antiguo.aImagen.path)
    except sender.DoesNotExist:
        pass
