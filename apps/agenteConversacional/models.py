from django.db import models
from pgvector.django import VectorField, HnswIndex
from apps.producto.models import Producto
from apps.usuario.models import Usuario
import uuid

class ProductoEmbedding(models.Model):
    id_embedding = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    producto = models.OneToOneField(Producto, on_delete=models.CASCADE, related_name='embedding')
    texto = models.TextField()  # Texto concatenado usado para generar el embedding
    vector = VectorField(dimensions=384)  # Vector de 384 dimensiones para all-MiniLM-L6-v2
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "producto_embedding"
        verbose_name = "Embedding de Producto"
        verbose_name_plural = "Embeddings de Productos"
        indexes = [
            HnswIndex(
                name='vector_cos_idx',
                fields=['vector'],
                opclasses=['vector_cosine_ops']
            )
        ]

    def __str__(self):
        return f"Embedding de {self.producto.nombre}"


class Conversacion(models.Model):
    id_conversacion = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name='conversaciones')
    session_key = models.CharField(max_length=255, null=True, blank=True, db_index=True)  # Para clientes no autenticados
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "conversacion"
        verbose_name = "Conversación"
        verbose_name_plural = "Conversaciones"

    def __str__(self):
        if self.usuario:
            return f"Conversación {self.id_conversacion} - Propietario: {self.usuario.usuario}"
        return f"Conversación {self.id_conversacion} - Cliente Anónimo"


class Mensaje(models.Model):
    id_mensaje = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversacion = models.ForeignKey(Conversacion, on_delete=models.CASCADE, related_name='mensajes')
    role = models.CharField(max_length=20)  # 'usuario' o 'asistente'
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "conversacion_mensaje"
        verbose_name = "Mensaje"
        verbose_name_plural = "Mensajes"
        ordering = ['created_at']

    def __str__(self):
        return f"{self.role.capitalize()}: {self.content[:30]}..."


class AuditoriaHerramienta(models.Model):
    id_auditoria = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name='auditorias_herramienta')
    conversacion = models.ForeignKey(Conversacion, on_delete=models.SET_NULL, null=True, blank=True, related_name='auditorias_herramienta')
    rol = models.CharField(max_length=20)
    herramienta = models.CharField(max_length=100)
    modelo = models.CharField(max_length=100, null=True, blank=True)
    operacion = models.CharField(max_length=50, null=True, blank=True)
    cantidad_resultados = models.IntegerField(default=0)
    estado = models.CharField(max_length=20)  # 'EXITOSO', 'DENEGADO', 'ERROR'
    motivo = models.CharField(max_length=100, null=True, blank=True)
    nivel_riesgo = models.CharField(max_length=10, default="BAJO")
    duracion = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "auditoria_herramienta"
        verbose_name = "Auditoría de Herramienta"
        verbose_name_plural = "Auditorías de Herramientas"

    def __str__(self):
        usr_str = self.usuario.usuario if self.usuario else "Anónimo"
        return f"{usr_str} ({self.rol}) - {self.herramienta} - {self.estado}"
