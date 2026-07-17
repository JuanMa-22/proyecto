import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from apps.agenteConversacional.models import Conversacion
from apps.usuario.models import Usuario
from apps.agenteConversacional.middleware.limite_tasa import AgenteConversacionalLimiteTasaMiddleware

logger = logging.getLogger(__name__)

class AgenteConversacionalConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # 1. Obtener la sesión
        self.session = self.scope.get("session", {})
        self.usuario_id = self.session.get("usuario_id")
        self.session_key = self.session.session_key
        
        # 2. Determinar el rol real
        # Ignorar cualquier información de rol o parámetro enviados desde el frontend (JS o query params)
        # La autenticación se verifica estrictamente con la sesión de Django (usuario_id)
        user = self.scope.get("user")
        self.es_propietario = False
        
        # 1. Priorizar scope["user"] si está autenticado
        if user and user.is_authenticated:
            try:
                usuario = await self.obtener_usuario(user.pk)
                if usuario and usuario.estado and usuario.rol and usuario.rol.nombre.lower() == 'administrador':
                    self.es_propietario = True
            except Exception as e:
                logger.error(f"Error al verificar scope['user'] en connect: {e}")
                
        # 2. Recurrir a la sesión personalizada únicamente como mecanismo compatible
        if not self.es_propietario and self.usuario_id:
            try:
                usuario = await self.obtener_usuario(self.usuario_id)
                if usuario and usuario.estado and usuario.rol and usuario.rol.nombre.lower() == 'administrador':
                    self.es_propietario = True
            except Exception as e:
                logger.error(f"Error al verificar usuario_id de sesion en connect: {e}")

        # 3. Crear o recuperar la conversación correspondiente
        self.conversacion = await self.obtener_o_crear_conversacion()
        self.conversacion_id = str(self.conversacion.id_conversacion)

        # 4. Aceptar conexión de canal WebSocket
        await self.accept()
        logger.info(f"WebSocket conectado para conversación ID {self.conversacion_id} (Propietario: {self.es_propietario})")

    async def disconnect(self, close_code):
        logger.info(f"WebSocket desconectado para conversación ID {self.conversacion_id} con código {close_code}")

    async def receive(self, text_data):
        try:
            try:
                data = json.loads(text_data)
            except json.JSONDecodeError:
                await self.send(text_data=json.dumps({
                    "type": "error",
                    "message": "Formato de mensaje no válido."
                }))
                return

            # FASE 12. SEGURIDAD DEL WEBSOCKET
            # 1. No aceptar llamadas a herramientas ni campos no autorizados desde el frontend
            allowed_keys = {"message"}
            received_keys = set(data.keys())
            if not received_keys.issubset(allowed_keys) or "tool" in data or "function" in data or "rol" in data:
                await self.send(text_data=json.dumps({
                    "type": "error",
                    "message": "Solicitud no permitida."
                }))
                return

            mensaje_usuario = data.get("message", "").strip()
            
            if not mensaje_usuario:
                return

            # 2. Longitud máxima del mensaje (1000 caracteres)
            if len(mensaje_usuario) > 1000:
                await self.send(text_data=json.dumps({
                    "type": "error",
                    "message": "Tu consulta es demasiado extensa. Intenta resumirla."
                }))
                return

            # Rate Limiting utilizando Redis
            identificador = self.usuario_id or self.session_key or self.channel_name
            if not AgenteConversacionalLimiteTasaMiddleware.verificar_rate_limit_rol(identificador, self.es_propietario):
                await self.send(text_data=json.dumps({
                    "type": "error",
                    "message": "Has realizado varias consultas en poco tiempo. Inténtalo nuevamente dentro de unos minutos."
                }))
                return

            # Disparar tarea Celery de forma no bloqueante para el event loop ASGI
            from asgiref.sync import sync_to_async
            from apps.agenteConversacional.tareas import procesar_mensaje_agente_task
            await sync_to_async(procesar_mensaje_agente_task.delay)(
                self.conversacion_id,
                mensaje_usuario,
                self.es_propietario,
                self.channel_name
            )

        except Exception as e:
            logger.error(f"Error procesando mensaje en receive: {e}")
            await self.send(text_data=json.dumps({
                "type": "error",
                "message": "Ocurrió un error inesperado al procesar tu solicitud."
            }))

    # Handler para reenviar los eventos enviados desde la tarea Celery al cliente WebSocket
    async def agent_event(self, event):
        payload = event.get("event")
        await self.send(text_data=json.dumps(payload))

    @database_sync_to_async
    def obtener_usuario(self, usuario_id):
        """
        Recupera el usuario con su rol.
        """
        try:
            return Usuario.objects.select_related('rol').get(pk=usuario_id)
        except Usuario.DoesNotExist:
            return None

    @database_sync_to_async
    def obtener_o_crear_conversacion(self):
        """
        Recupera la última conversación o crea una nueva, según el usuario o la sesión de cliente.
        """
        if self.es_propietario:
            try:
                usuario = Usuario.objects.get(pk=self.usuario_id)
                # Buscar la conversación más reciente del propietario
                conv = Conversacion.objects.filter(usuario=usuario).order_by('-created_at').first()
                if not conv:
                    conv = Conversacion.objects.create(usuario=usuario)
                return conv
            except Usuario.DoesNotExist:
                pass
                
        if self.session_key:
            conv = Conversacion.objects.filter(session_key=self.session_key).order_by('-created_at').first()
            if not conv:
                conv = Conversacion.objects.create(session_key=self.session_key)
            return conv
            
        # Fallback si no hay sesión iniciada ni de Django
        return Conversacion.objects.create()
