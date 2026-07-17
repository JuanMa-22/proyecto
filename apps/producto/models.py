from django.db import models
import uuid
from apps.categoria.models import Categoria
from apps.marca.models import Marca
from django.utils.text import slugify

# Create your models here.
class Producto(models.Model):
    id_producto = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=100)
    slug = models.SlugField(max_length=150, unique=True, blank=True, null=True)
    descripcion = models.TextField(blank=True, null=True)
    precio_actual = models.DecimalField(max_digits=10, decimal_places=2)
    precio_usd = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    stock = models.IntegerField()
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE)
    marca = models.ForeignKey(Marca, on_delete=models.CASCADE)
    imagen = models.ImageField(upload_to='productos/', null=True, blank=True)
    estado = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "producto"
        verbose_name = "Producto"
        verbose_name_plural = "Productos"

    @property
    def especificacion(self):
        from apps.productoEspecificacion.models import ProductoEspecificacion
        return self.productoespecificacion_set.filter(estado=True).first()

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.nombre)
            slug = base_slug
            num = 1
            while Producto.objects.filter(slug=slug).exclude(id_producto=self.id_producto).exists():
                slug = f"{base_slug}-{num}"
                num += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre