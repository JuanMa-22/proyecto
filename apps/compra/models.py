from django.db import models
from apps.proveedor.models import Proveedor
from apps.usuario.models import Usuario
import uuid
from django.core.exceptions import ValidationError
from django.utils import timezone

def validate_not_past(value):
    if value < timezone.localdate():
        raise ValidationError("La fecha no puede ser anterior a hoy.")

# Create your models here.
class Compra(models.Model):
    id_compra = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    proveedor = models.ForeignKey(Proveedor, on_delete=models.CASCADE)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    fecha = models.DateField(validators=[validate_not_past])
    observacion = models.TextField(blank=True, null=True)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    tipo_cambio_valor = models.DecimalField(max_digits=10, decimal_places=2, default=6.96)
    estado = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        db_table = "compra"
        verbose_name = "Compra"
        verbose_name_plural = "Compras"
    def __str__(self):
        return str(self.id_compra)

    @property
    def total_bs(self):
        return self.total * self.tipo_cambio_valor