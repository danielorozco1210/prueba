from django.core.management.base import BaseCommand
from django.db import connection
from ...models import *

class Command(BaseCommand):
    help = 'Resetear todos los datos y IDs'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--confirmar',
            action='store_true',
            help='Confirmar que quiere borrar todos los datos',
        )
    
    def handle(self, *args, **options):
        if not options['confirmar']:
            self.stdout.write(
                self.style.WARNING('Este comando borrará TODOS los datos del portfolio.')
            )
            self.stdout.write(
                'Para continuar, ejecute: python manage.py resetear_ids --confirmar'
            )
            return
        
        self.stdout.write('Borrando todos los datos...')
        
        Transaccion.objects.all().delete()
        PesoActivo.objects.all().delete()
        ValorPortafolio.objects.all().delete()
        CantidadActivo.objects.all().delete()
        PesoPortafolio.objects.all().delete()
        Precio.objects.all().delete()
        Activo.objects.all().delete()
        Portafolio.objects.all().delete()
        
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM sqlite_sequence WHERE name='portfolio_portafolio'")
            cursor.execute("DELETE FROM sqlite_sequence WHERE name='portfolio_activo'")
            cursor.execute("DELETE FROM sqlite_sequence WHERE name='portfolio_precio'")
            cursor.execute("DELETE FROM sqlite_sequence WHERE name='portfolio_pesoportafolio'")
            cursor.execute("DELETE FROM sqlite_sequence WHERE name='portfolio_cantidadactivo'")
            cursor.execute("DELETE FROM sqlite_sequence WHERE name='portfolio_valorportafolio'")
            cursor.execute("DELETE FROM sqlite_sequence WHERE name='portfolio_pesoactivo'")
            cursor.execute("DELETE FROM sqlite_sequence WHERE name='portfolio_transaccion'")
        
        self.stdout.write(self.style.SUCCESS('Datos borrados y secuencias reseteadas'))
        self.stdout.write('Ahora ejecute: python manage.py cargar_datos --archivo datos.xlsx')
        self.stdout.write('O: python manage.py crear_datos_prueba')