from django.db import models
from apps.compra.models import Compra
from apps.producto.models import Producto
import uuid
# Create your models here.
class DetalleCompra(models.Model):
    id_detalleCompra = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    compra = models.ForeignKey(Compra, on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.IntegerField()
    precio_compra = models.DecimalField(max_digits=10, decimal_places=2)
    precio_venta = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    estado = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = "detalleCompra"
        verbose_name = "DetalleCompra"
        verbose_name_plural = "DetalleCompras"
    def __str__(self):
        return self.id_detalleCompra
