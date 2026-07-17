from django.db import models
from apps.usuario.models import Usuario
import uuid
from django.core.validators import RegexValidator

# Create your models here.
class Cliente(models.Model):
    id_cliente = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=100, validators=[
        RegexValidator(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$', 'Solo se permiten letras en el nombre')
    ])
    apellido = models.CharField(max_length=100, validators=[
        RegexValidator(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$', 'Solo se permiten letras en el apellido')
    ])
    email = models.EmailField(max_length=100)
    telefono = models.CharField(max_length=15, validators=[
        RegexValidator(r'^[0-9]+$', 'Solo se permiten números en el teléfono')
    ])
    direccion = models.CharField(max_length=100)
    ci = models.CharField(max_length=20, validators=[
        RegexValidator(r'^[0-9]+$', 'Solo se permiten números en el CI/NIT')
    ])
    estado = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "cliente"
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"

    def __str__(self):
        return self.nombre
    