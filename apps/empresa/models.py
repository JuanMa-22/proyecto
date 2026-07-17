from django.db import models
import uuid
from django.core.validators import RegexValidator

class Empresa(models.Model):
    id_empresa = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(
        max_length=150,
        validators=[
            RegexValidator(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ0-9\s\.\,\-\&]+$', 'Solo se permiten letras, números y caracteres válidos en el nombre')
        ],
        verbose_name="Nombre de la Empresa"
    )
    nit = models.CharField(
        max_length=30,
        validators=[
            RegexValidator(r'^[0-9]+$', 'Solo se permiten números en el NIT')
        ],
        verbose_name="NIT / Identificación Tributaria"
    )
    direccion = models.CharField(max_length=255, verbose_name="Dirección Física")
    telefono = models.CharField(
        max_length=50,
        validators=[
            RegexValidator(r'^[0-9\+\-\s]+$', 'Solo se permiten números, espacios y los signos + o - en el teléfono')
        ],
        verbose_name="Teléfono / Celular"
    )
    email = models.EmailField(verbose_name="Correo Electrónico")
    logo = models.ImageField(upload_to='empresa/', null=True, blank=True, verbose_name="Logo de la Empresa")
    ciudad = models.CharField(
        max_length=100,
        default="La Paz",
        validators=[
            RegexValidator(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$', 'Solo se permiten letras en el nombre de la ciudad')
        ],
        verbose_name="Ciudad/País"
    )
    latitud = models.DecimalField(
        max_digits=18,
        decimal_places=15,
        null=True,
        blank=True,
        verbose_name="Latitud"
    )
    longitud = models.DecimalField(
        max_digits=18,
        decimal_places=15,
        null=True,
        blank=True,
        verbose_name="Longitud"
    )
    google_maps_link = models.URLField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name="Enlace de Google Maps"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "empresa"
        verbose_name = "Datos de la Empresa"
        verbose_name_plural = "Datos de la Empresa"

    def __str__(self):
        return self.nombre
