from django.db import models
import uuid
from apps.producto.models import Producto
from apps.detalleCompra.models import DetalleCompra
from apps.detalleVenta.models import DetalleVenta
from apps.proveedor.models import Proveedor


class LoteProducto(models.Model):
    """
    Representa un lote de productos ingresado al inventario mediante una compra.
    Implementa la metodología PEPS (Primero en Entrar, Primero en Salir / FIFO).
    Cada compra genera un lote independiente con su fecha de entrada y costo unitario.
    """
    id_lote = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        related_name='lotes',
        verbose_name='Producto'
    )
    detalle_compra = models.ForeignKey(
        DetalleCompra,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lote',
        verbose_name='Detalle de Compra'
    )
    proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Proveedor'
    )
    fecha_entrada = models.DateField(verbose_name='Fecha de Entrada')
    cantidad_inicial = models.IntegerField(verbose_name='Cantidad Inicial')
    cantidad_disponible = models.IntegerField(verbose_name='Cantidad Disponible')
    precio_costo_usd = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Costo Unitario (USD)'
    )
    estado = models.BooleanField(default=True, verbose_name='Activo')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'lote_producto'
        verbose_name = 'Lote de Producto'
        verbose_name_plural = 'Lotes de Productos'
        ordering = ['fecha_entrada', 'created_at']

    def __str__(self):
        return f"Lote {str(self.id_lote)[:8]} | {self.producto.nombre} | {self.fecha_entrada} | Disp: {self.cantidad_disponible}"

    @property
    def esta_agotado(self):
        return self.cantidad_disponible <= 0

    @property
    def porcentaje_consumido(self):
        if self.cantidad_inicial == 0:
            return 100
        return round(((self.cantidad_inicial - self.cantidad_disponible) / self.cantidad_inicial) * 100, 1)


class LoteConsumo(models.Model):
    """
    Registro de cada descuento aplicado a un lote al momento de una venta (trazabilidad PEPS).
    Permite saber exactamente de qué lote salió cada unidad vendida.
    """
    id_consumo = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lote = models.ForeignKey(
        LoteProducto,
        on_delete=models.CASCADE,
        related_name='consumos',
        verbose_name='Lote'
    )
    detalle_venta = models.ForeignKey(
        DetalleVenta,
        on_delete=models.CASCADE,
        related_name='consumos_lote',
        verbose_name='Detalle de Venta'
    )
    cantidad = models.PositiveIntegerField(verbose_name='Cantidad Consumida')
    fecha_consumo = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Consumo')

    class Meta:
        db_table = 'lote_consumo'
        verbose_name = 'Consumo de Lote'
        verbose_name_plural = 'Consumos de Lotes'
        ordering = ['-fecha_consumo']

    def __str__(self):
        return f"Consumo {self.cantidad} u. de Lote {str(self.lote.id_lote)[:8]} | Venta {str(self.detalle_venta.venta.id_venta)[:8]}"
