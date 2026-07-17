from django.db import models
import uuid

# Create your models here.
class tipoMovimiento(models.Model):
    TIPOS_CHOICES= [
        ('ENTRADA', 'Entrada'),
        ('SALIDA', 'Salida'),
    ]
    id_tipoMovimiento = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=100, choices=TIPOS_CHOICES)
    estado = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tipoMovimiento"
        verbose_name = "Tipo de Movimiento"
        verbose_name_plural = "Tipos de Movimientos"

    def __str__(self):
        return self.nombre