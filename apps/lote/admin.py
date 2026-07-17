from django.contrib import admin
from .models import LoteProducto, LoteConsumo


@admin.register(LoteProducto)
class LoteProductoAdmin(admin.ModelAdmin):
    list_display = (
        'id_lote', 'producto', 'proveedor', 'fecha_entrada',
        'cantidad_inicial', 'cantidad_disponible', 'precio_costo_usd', 'estado'
    )
    list_filter = ('estado', 'fecha_entrada', 'proveedor')
    search_fields = ('producto__nombre', 'proveedor__nombre')
    readonly_fields = ('id_lote', 'created_at', 'updated_at')
    ordering = ('fecha_entrada', 'created_at')


@admin.register(LoteConsumo)
class LoteConsumoAdmin(admin.ModelAdmin):
    list_display = ('id_consumo', 'lote', 'detalle_venta', 'cantidad', 'fecha_consumo')
    list_filter = ('fecha_consumo',)
    search_fields = ('lote__producto__nombre',)
    readonly_fields = ('id_consumo', 'fecha_consumo')
    ordering = ('-fecha_consumo',)
