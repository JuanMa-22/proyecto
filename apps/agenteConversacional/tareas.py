from celery import shared_task
import logging
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from apps.producto.models import Producto
from .models import ProductoEmbedding
from .embeddings import EmbeddingsGenerator
from .llm import ejecutar_agente_stream

logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────
# PUENTE PARA ENVIAR ACTUALIZACIONES EN STREAMING POR ASGI
# ────────────────────────────────────────────────────────
class ChannelLayerAgentBridge:
    """
    Clase que implementa los mismos métodos de envío que espera el agente LLM,
    pero los envía asíncronamente a través del Channel Layer al WebSocket del usuario.
    """
    def __init__(self, channel_name):
        self.channel_name = channel_name
        self.channel_layer = get_channel_layer()

    def enviar_token(self, token):
        async_to_sync(self.channel_layer.send)(
            self.channel_name,
            {
                "type": "agent_event",
                "event": {"type": "token", "token": token}
            }
        )

    def enviar_typing(self, is_typing):
        async_to_sync(self.channel_layer.send)(
            self.channel_name,
            {
                "type": "agent_event",
                "event": {"type": "typing", "is_typing": is_typing}
            }
        )

    def enviar_done(self, full_text):
        async_to_sync(self.channel_layer.send)(
            self.channel_name,
            {
                "type": "agent_event",
                "event": {"type": "done", "full_text": full_text}
            }
        )

    def enviar_error(self, message):
        async_to_sync(self.channel_layer.send)(
            self.channel_name,
            {
                "type": "agent_event",
                "event": {"type": "error", "message": message}
            }
        )


# ────────────────────────────────────────────────────────
# TAREAS CELERY
# ────────────────────────────────────────────────────────

@shared_task(name="apps.agenteConversacional.tareas.procesar_mensaje_agente_task")
def procesar_mensaje_agente_task(conversacion_id, mensaje_usuario, es_propietario, channel_name):
    """
    Tarea Celery principal que ejecuta el razonamiento RAG y llamadas a Groq de forma asíncrona,
    evitando bloquear los hilos principales del servidor web ASGI.
    """
    logger.info(f"Iniciando tarea Celery para procesar mensaje del usuario en conversación: {conversacion_id}")
    bridge = ChannelLayerAgentBridge(channel_name)
    ejecutar_agente_stream(conversacion_id, mensaje_usuario, es_propietario, bridge)
    return "FINISHED"


@shared_task(name="apps.agenteConversacional.tareas.actualizar_embedding_producto_task")
def actualizar_embedding_producto_task(producto_id):
    """
    Tarea de Celery para generar o actualizar el embedding de un único producto.
    """
    try:
        producto = Producto.objects.get(pk=producto_id)
        generator = EmbeddingsGenerator()
        
        texto_indexar = generator.generar_texto_producto(producto)
        vector_embedding = generator.generar_embedding(texto_indexar)
        
        # Guardar en base de datos
        ProductoEmbedding.objects.update_or_create(
            producto=producto,
            defaults={
                "texto": texto_indexar,
                "vector": vector_embedding
            }
        )
        logger.info(f"Embedding actualizado para el producto: {producto.nombre}")
        return f"OK: {producto.nombre}"
    except Producto.DoesNotExist:
        logger.error(f"El producto con ID {producto_id} no existe.")
        return "ERROR: Producto no existe"
    except Exception as e:
        logger.error(f"Error actualizando embedding para ID {producto_id}: {e}")
        return f"ERROR: {str(e)}"


@shared_task(name="apps.agenteConversacional.tareas.regenerar_todos_los_embeddings_task")
def regenerar_todos_los_embeddings_task():
    """
    Tarea de Celery para recrear los embeddings de TODOS los productos activos.
    """
    try:
        productos = Producto.objects.filter(estado=True)
        generator = EmbeddingsGenerator()
        creados = 0
        
        logger.info(f"Iniciando regeneración de embeddings para {productos.count()} productos...")
        
        for producto in productos:
            texto_indexar = generator.generar_texto_producto(producto)
            vector_embedding = generator.generar_embedding(texto_indexar)
            
            ProductoEmbedding.objects.update_or_create(
                producto=producto,
                defaults={
                    "texto": texto_indexar,
                    "vector": vector_embedding
                }
            )
            creados += 1
            
        logger.info(f"Regeneración completada. {creados} embeddings procesados.")
        return f"SUCCESS: {creados} embeddings creados/actualizados."
    except Exception as e:
        logger.error(f"Error regenerando embeddings generales: {e}")
        return f"ERROR: {str(e)}"


from celery.signals import task_postrun
from django.db import connections

@task_postrun.connect
def close_db_connections(*args, **kwargs):
    """
    Cierra todas las conexiones a la base de datos al finalizar cada tarea de Celery,
    previniendo fugas de conexiones y caídas de base de datos en producción.
    """
    try:
        connections.close_all()
        logger.info("[PERF] Conexiones a la base de datos cerradas correctamente tras la ejecución de la tarea.")
    except Exception as e:
        logger.error(f"Error cerrando conexiones a la base de datos en Celery post-run: {e}")


from celery.signals import worker_process_init

@worker_process_init.connect
def precalentar_worker(*args, **kwargs):
    """
    Precalienta el modelo de embeddings SentenceTransformer al iniciar cada subproceso worker de Celery
    (después del fork), evitando bloqueos y candados huérfanos heredados del proceso padre.
    """
    try:
        logger.info("Precalentando modelo SentenceTransformer en el subproceso worker recién forkeado...")
        EmbeddingsGenerator().model
    except Exception as e:
        logger.error(f"Error precalentando modelo en el worker: {e}")
