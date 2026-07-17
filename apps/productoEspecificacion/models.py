from django.db import models
from apps.producto.models import Producto
# Create your models here.

class ProductoEspecificacion(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    socket = models.CharField(max_length=100, null=True, blank=True)
    chipset = models.CharField(max_length=100, null=True, blank=True)
    tipo_ram = models.CharField(max_length=100, null=True, blank=True)
    vram = models.CharField(max_length=100, null=True, blank=True)
    watts = models.CharField(max_length=100, null=True, blank=True)
    velocidad_ram = models.CharField(max_length=100, null=True, blank=True)
    almacenamiento = models.CharField(max_length=100, null=True, blank=True)
    pci = models.CharField(max_length=100, null=True, blank=True)
    estado = models.BooleanField(default=True)
    fechaCreacion = models.DateTimeField(auto_now_add=True)
    fechaActualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "productoEspecificacion"
        verbose_name = "Especificación de Producto"
        verbose_name_plural = "Especificaciones de Productos"

    def __str__(self):
        return f"Especificación de {self.producto.nombre}"
    
