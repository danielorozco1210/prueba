from django.core.management.base import BaseCommand
from ...etl import cargar_datos_excel, calcular_cantidades_iniciales, calcular_valores_historicos
import os

class Command(BaseCommand):
    help = 'Cargar datos desde el archivo Excel y calcular valores iniciales'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--archivo',
            type=str,
            help='Ruta al archivo Excel con los datos',
            default='datos.xlsx'
        )
    
    def handle(self, *args, **options):
        archivo = options['archivo']
        
        if not os.path.exists(archivo):
            self.stdout.write(
                self.style.ERROR(f'El archivo {archivo} no existe')
            )
            return
        
        self.stdout.write('Iniciando carga de datos...')
        
        if cargar_datos_excel(archivo):
            self.stdout.write(
                self.style.SUCCESS('Datos del Excel cargados exitosamente')
            )
        else:
            self.stdout.write(
                self.style.ERROR('Error cargando datos del Excel')
            )
            return
        
        if calcular_cantidades_iniciales():
            self.stdout.write(
                self.style.SUCCESS('Cantidades iniciales calculadas')
            )
        else:
            self.stdout.write(
                self.style.ERROR('Error calculando cantidades iniciales')
            )
            return
        
        if calcular_valores_historicos():
            self.stdout.write(
                self.style.SUCCESS('Valores históricos calculados')
            )
        else:
            self.stdout.write(
                self.style.ERROR('Error calculando valores históricos')
            )
            return
        
        self.stdout.write(
            self.style.SUCCESS('¡Proceso completado exitosamente!')
        )