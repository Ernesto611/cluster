from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from entradas.models import CompraEntrada
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Elimina compras pendientes (excepto efectivo) con más de 1 día'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo muestra qué compras se eliminarían sin borrarlas',
        )

    def handle(self, *args, **options):

        fecha_limite = timezone.now() - timedelta(days=1)

        compras_a_eliminar = CompraEntrada.objects.filter(
            status_pago='pendiente',
            fecha_compra__lt=fecha_limite
        ).exclude(metodo_pago='efectivo')

        count = compras_a_eliminar.count()

        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING(f'DRY RUN: Se eliminarían {count} compras pendientes')
            )
            for compra in compras_a_eliminar:
                self.stdout.write(f'  - Compra {compra.idCompra}: {compra.entrada.aNombre} - {compra.usuario.aNombre}')
        else:
            if count > 0:
                compras_a_eliminar.delete()
                self.stdout.write(
                    self.style.SUCCESS(f'Se eliminaron {count} compras pendientes exitosamente')
                )
                logger.info(f'Cleanup: Se eliminaron {count} compras pendientes')
            else:
                self.stdout.write(
                    self.style.SUCCESS('No hay compras pendientes para eliminar')
                )
                logger.info('Cleanup: No hay compras pendientes para eliminar')
