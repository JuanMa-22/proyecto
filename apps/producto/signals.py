from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Producto
from apps.productoEspecificacion.models import ProductoEspecificacion
from apps.agenteConversacional.tareas import actualizar_embedding_producto_task
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Producto)
def producto_post_save(sender, instance, created, **kwargs):
    """
    Se dispara al crear o modificar un producto.
    Lanza la tarea de Celery para generar/actualizar el embedding en segundo plano.
    """
    if kwargs.get('raw', False):
        return
    try:
        actualizar_embedding_producto_task.delay(str(instance.id_producto))
    except Exception as e:
        logger.error(f"Error al programar la generación de embedding para producto {instance.id_producto}: {e}")

@receiver(post_save, sender=ProductoEspecificacion)
def especificaciones_post_save(sender, instance, created, **kwargs):
    """
    Se dispara al crear o modificar especificaciones técnicas.
    Regenera el embedding del producto asociado, ya que los embeddings contienen especificaciones.
    """
    if kwargs.get('raw', False):
        return
    if instance.producto:
        try:
            actualizar_embedding_producto_task.delay(str(instance.producto.id_producto))
        except Exception as e:
            logger.error(f"Error al programar la generación de embedding desde especificaciones: {e}")
