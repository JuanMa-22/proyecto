from django.db import models
from apps.rol.models import Rol
import uuid
from django.core.validators import RegexValidator

# Create your models here.
class Usuario(models.Model):
    id_usuario = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
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
        RegexValidator(r'^[0-9]+$', 'Solo se permiten números en el CI')
    ])
    usuario = models.CharField(max_length=100)
    password = models.CharField(max_length=100)
    rol = models.ForeignKey(Rol, on_delete=models.CASCADE)
    estado = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "usuario"
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"

    def __str__(self):
        return self.usuario


class IntentoLogin(models.Model):
    usuario_ingresado = models.CharField(max_length=150, db_index=True)
    ip_origen = models.GenericIPAddressField(db_index=True)
    cantidad_intentos = models.IntegerField(default=0)
    bloqueado_hasta = models.DateTimeField(null=True, blank=True)
    ultimo_intento = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "intento_login"
        verbose_name = "Intento de Login"
        verbose_name_plural = "Intentos de Login"

    def __str__(self):
        return f"{self.usuario_ingresado} desde {self.ip_origen} ({self.cantidad_intentos} intentos)"
    
