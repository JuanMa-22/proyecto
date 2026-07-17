from django.db import models
import uuid
from apps.producto.models import Producto
from django.core.validators import MinValueValidator

class Inventario(models.Model):
    id_inventario = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    producto = models.OneToOneField(Producto, on_delete=models.CASCADE, related_name='inventario')
    stock_minimo = models.IntegerField(default=5, validators=[MinValueValidator(0)], verbose_name="Stock Mínimo")
    stock_maximo = models.IntegerField(default=100, validators=[MinValueValidator(0)], verbose_name="Stock Máximo")
    ubicacion = models.CharField(max_length=150, default="Almacén Principal", verbose_name="Ubicación Física")
    fecha_ultimo_inventario = models.DateTimeField(auto_now=True, verbose_name="Última Actualización")

    class Meta:
        db_table = "inventario"
        verbose_name = "Inventario de Producto"
        verbose_name_plural = "Inventarios de Productos"

    def __str__(self):
        return f"Inventario de {self.producto.nombre}"

    @property
    def estado_stock(self):
        """Calcula dinámicamente si el stock actual está bajo, agotado, normal o sobre-stock."""
        stock_actual = self.producto.stock
        if stock_actual == 0:
            return "Agotado"
        elif stock_actual <= self.stock_minimo:
            return "Stock Bajo"
        elif stock_actual >= self.stock_maximo:
            return "Sobre-stock"
        return "Normal"

    @property
    def valoracion_total_usd(self):
        """Valora el inventario actual de este producto en USD."""
        return self.producto.stock * self.producto.precio_usd

    @property
    def valoracion_total_bs(self):
        """Valora el inventario actual de este producto en Bolivianos."""
        return self.producto.stock * self.producto.precio_actual
