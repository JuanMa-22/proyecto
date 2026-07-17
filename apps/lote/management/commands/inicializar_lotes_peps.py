"""
Comando de management: python manage.py inicializar_lotes_peps

Uso:
    python manage.py inicializar_lotes_peps

Crea un LoteProducto inicial para cada producto con stock > 0
que aún no tenga lotes PEPS asignados.
Ejecutar UNA SOLA VEZ después de la primera migración del módulo lote.
"""
from django.core.management.base import BaseCommand
from apps.lote.servicios import inicializar_lotes_existentes


class Command(BaseCommand):
    help = 'Inicializa los lotes PEPS para productos existentes con stock actual.'

    def handle(self, *args, **options):
        self.stdout.write('Inicializando/actualizando lotes PEPS para productos existentes...')
        creados, actualizados = inicializar_lotes_existentes()

        if creados > 0:
            self.stdout.write(
                self.style.SUCCESS(f'✅ Se crearon {creados} lote(s) PEPS nuevos.')
            )
        if actualizados > 0:
            self.stdout.write(
                self.style.SUCCESS(f'✅ Se actualizaron {actualizados} lote(s) con proveedor y fecha de compra.')
            )
        if creados == 0 and actualizados == 0:
            self.stdout.write(
                self.style.WARNING('ℹ️  Todos los lotes ya tienen proveedor asignado. Nada que actualizar.')
            )
