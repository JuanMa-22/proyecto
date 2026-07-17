from django.db import models
from apps.producto.models import Producto
from apps.tipoCambio.models import TipoCambio
import uuid
# Create your models here.
class HistorialPrecio(models.Model):
    id_historialPrecio = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    precio_compra = models.DecimalField(max_digits=10, decimal_places=2)
    precio_venta = models.DecimalField(max_digits=10, decimal_places=2)
    tipo_cambio = models.ForeignKey(TipoCambio, on_delete=models.CASCADE)
    fecha_inicio = models.DateTimeField(auto_now_add=True)
    fecha_fin = models.DateTimeField(null=True, blank=True)
    estado = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "historialPrecio"
        verbose_name = "HistorialPrecio"
        verbose_name_plural = "HistorialPrecios"

    def __str__(self):
        return str(self.id_historialPrecio)