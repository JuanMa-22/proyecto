from django.apps import AppConfig
from django.db.models.signals import post_save
from django.dispatch import receiver

class AgenteConversacionalConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.agenteConversacional'
    verbose_name = 'Agente Conversacional'

    def ready(self):
        # Conectar las señales de forma segura cuando la app esté lista
        from apps.producto.models import Producto
        from apps.productoEspecificacion.models import ProductoEspecificacion
        from .tareas import actualizar_embedding_producto_task

        @receiver(post_save, sender=Producto)
        def al_guardar_producto(sender, instance, **kwargs):
            # Evitar ejecutar durante la carga de datos iniciales o fixtures (raw=True)
            if kwargs.get('raw', False):
                return
            # Solo indexar si el producto está activo
            if instance.estado:
                actualizar_embedding_producto_task.delay(str(instance.pk))

        @receiver(post_save, sender=ProductoEspecificacion)
        def al_guardar_especificacion(sender, instance, **kwargs):
            # Evitar ejecutar durante la carga de datos iniciales o fixtures (raw=True)
            if kwargs.get('raw', False):
                return
            # Si se actualizan especificaciones, regenerar el embedding del producto relacionado
            if instance.estado and instance.producto:
                actualizar_embedding_producto_task.delay(str(instance.producto.pk))
