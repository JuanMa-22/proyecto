from django.db import models
import uuid
from apps.cliente.models import Cliente
from apps.usuario.models import Usuario
from apps.producto.models import Producto
from apps.tipoMovimiento.models import tipoMovimiento
from django.core.exceptions import ValidationError
from django.utils import timezone

def validate_not_past(value):
    if value < timezone.localdate():
        raise ValidationError("La fecha no puede ser anterior a hoy.")

# Create your models here.
class Venta(models.Model):
    id_venta = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    fecha = models.DateField(validators=[validate_not_past])
    total = models.DecimalField(max_digits=10, decimal_places=2)
    tipo_cambio_valor = models.DecimalField(max_digits=10, decimal_places=2, default=6.96)
    estado = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = "venta"
        verbose_name = "Venta"
        verbose_name_plural = "Ventas"

    def __str__(self):
        return self.id_venta
