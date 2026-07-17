from django.db import models
import uuid
from django.core.validators import RegexValidator

# Create your models here.
class Proveedor(models.Model):
    id_proveedor = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=100, validators=[
        RegexValidator(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$', 'Solo se permiten letras en el nombre')
    ])
    telefono = models.CharField(max_length=15, validators=[
        RegexValidator(r'^[0-9]+$', 'Solo se permiten números en el teléfono')
    ])
    estado = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        db_table = "proveedor"
        verbose_name = "Proveedor"
        verbose_name_plural = "Proveedores"
    def __str__(self):
        return self.nombre