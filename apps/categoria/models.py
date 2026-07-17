from django.db import models
import uuid
from django.utils.text import slugify

# Create your models here.

class Categoria(models.Model):
    id_categoria = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=100)
    slug = models.SlugField(max_length=150, unique=True, blank=True, null=True)
    descripcion = models.TextField(blank=True, null=True)
    estado = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "categoria"
        verbose_name = "Categoria"
        verbose_name_plural = "Categorias"

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.nombre)
            slug = base_slug
            num = 1
            while Categoria.objects.filter(slug=slug).exclude(id_categoria=self.id_categoria).exists():
                slug = f"{base_slug}-{num}"
                num += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def total_productos_disponibles(self):
        return self.producto_set.filter(estado=True, stock__gt=0).count()

    def __str__(self):
        return self.nombre

