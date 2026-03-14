from django.db import models
from eventos.models import Evento
from actividades.models import Actividad

class Agenda(models.Model):
    idAgenda = models.AutoField(primary_key=True)
    idEvento = models.ForeignKey(Evento, on_delete=models.CASCADE, related_name='agendas')
    aNombre = models.CharField(max_length=255)
    lVisible = models.BooleanField(default=True)
    lActivo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.aNombre} - {self.idEvento.aNombre}"

class AgendaActividades(models.Model):
    idAgendaActividad = models.AutoField(primary_key=True)
    idAgenda = models.ForeignKey(Agenda, on_delete=models.CASCADE, related_name='agenda_actividades')
    idActividad = models.ForeignKey(Actividad, on_delete=models.CASCADE, related_name='agenda_actividades')

    class Meta:
        unique_together = ('idAgenda', 'idActividad')

    def __str__(self):
        return f"{self.idActividad.aNombre} en {self.idAgenda.aNombre}"
