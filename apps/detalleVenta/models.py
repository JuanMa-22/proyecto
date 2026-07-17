from django.db import models
from apps.venta.models import Venta
from apps.producto.models import Producto
import uuid
# Create your models here.
class DetalleVenta(models.Model):
    id_detalleVenta = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.IntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    descuento = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    estado = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    

    class Meta:
        db_table = "detalleVenta"
        verbose_name = "DetalleVenta"
        verbose_name_plural = "DetalleVentas"

    def __str__(self):
        return self.id_detalleVenta