from django.db import models
import uuid
# Create your models here.
class TipoCambio(models.Model):
    id_tipoCambio = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    fecha = models.DateField()
    estado = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        db_table = "tipoCambio"
        verbose_name = "TipoCambio"
        verbose_name_plural = "TipoCambios"
    def __str__(self):
        return self.id_tipoCambio
