from django.db import models
from apps.detalleVenta.models import DetalleVenta
from apps.detalleCompra.models import DetalleCompra
from apps.tipoMovimiento.models import tipoMovimiento
from apps.producto.models import Producto
import uuid
# Create your models here.
class Movimiento(models.Model):
    id_movimiento = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    detalleVenta = models.ForeignKey(DetalleVenta,on_delete=models.CASCADE,null=True,blank=True)
    detalleCompra = models.ForeignKey(DetalleCompra,on_delete=models.CASCADE,null=True,blank=True)
    tipoMovimiento = models.ForeignKey(tipoMovimiento, on_delete=models.CASCADE)
    cantidad = models.IntegerField()
    stock_anterior = models.IntegerField()
    stock_actual = models.IntegerField()
    motivo = models.CharField(max_length=255, null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)
    estado = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        db_table = "movimiento"
        verbose_name = "Movimiento"
        verbose_name_plural = "Movimientos"
    def __str__(self):
        return self.id_movimiento
