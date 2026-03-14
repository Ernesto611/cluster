from django.core.management.base import BaseCommand
from eventos.models import Evento
from django.utils.timezone import now

class Command(BaseCommand):
    help = 'Desactiva eventos cuya fecha de fin ya ha pasado'

    def handle(self, *args, **kwargs):
        eventos_a_desactivar = Evento.objects.filter(lActivo=True, fFechaFin__lt=now())
        total = eventos_a_desactivar.count()
        eventos_a_desactivar.update(lActivo=False)
        self.stdout.write(self.style.SUCCESS(f'{total} evento(s) desactivado(s).'))
