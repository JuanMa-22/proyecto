from django.core.cache import cache
from .models import Mensaje, Conversacion
import logging
import re

logger = logging.getLogger(__name__)

def resolver_conversacion_cache_key_y_ttl(conversacion_id: str):
    """
    Resuelve el namespace y el TTL de caché en Redis de acuerdo con el rol y la sesión.
    - Cliente: chat:cliente:<session_key> (TTL 1 hora)
    - Propietario: chat:propietario:<usuario_id>:<session_key> (TTL 8 horas)
    """
    try:
        conv = Conversacion.objects.select_related('usuario', 'usuario__rol').get(pk=conversacion_id)
        if conv.usuario and conv.usuario.rol and conv.usuario.rol.nombre.lower() == 'administrador':
            cache_key = f"chat:propietario:{conv.usuario.id_usuario}:{conv.session_key or conversacion_id}"
            ttl = 28800  # 8 horas
            return cache_key, ttl, conv
        else:
            cache_key = f"chat:cliente:{conv.session_key or conversacion_id}"
            ttl = 3600  # 1 hora
            return cache_key, ttl, conv
    except Exception as e:
        logger.warning(f"Error resolviendo cache key para {conversacion_id}: {e}")
        return f"chat:cliente:{conversacion_id}", 3600, None

def filtrar_contenido_sensible(content: str) -> str:
    """
    Filtra y redacta información sensible como contraseñas, hashes, claves API y tracebacks.
    """
    if not content:
        return content
        
    # Patrones para identificar datos sensibles
    patrones_limpieza = [
        (r'(?i)(api[_-]?key|secret[_-]?key|token|password|passwd|contraseña|session[_-]?key|access[_-]?token|refresh[_-]?token)\s*[:=]\s*["\']?[a-zA-Z0-9_\-\.\/]{8,}["\']?', r'\1: [REDACTADO_POR_SEGURIDAD]'),
        (r'(?i)(pbkdf2_sha256\$.*?\$[a-zA-Z0-9\/\+=\.]+)', '[HASH_REDACTADO]'),
        (r'(?i)(Traceback \(most recent call last\):[\s\S]+)', '[TRACEBACK_REDACTADO]'),
        (r'(?i)(SECRET_KEY\s*=\s*["\']?[a-zA-Z0-9!@#\$%\^&\*\(\)_\+\-\=\[\]\{\};:\'",\.<>\/\?\\\|`\s]+["\']?)', 'SECRET_KEY = [REDACTADO]')
    ]
    
    cleaned = content
    for pattern, repl in patrones_limpieza:
        cleaned = re.sub(pattern, repl, cleaned)
    return cleaned

def obtener_historial_conversacion(conversacion_id: str, max_mensajes: int = 5) -> list:
    """
    Recupera el historial de conversación desde la caché de Redis.
    Si no existe, lo carga desde la base de datos SQL y calienta la caché.
    """
    cache_key, ttl, conv = resolver_conversacion_cache_key_y_ttl(conversacion_id)
    historial = cache.get(cache_key)
    
    if historial is not None:
        logger.info(f"[CACHE HIT] Historial de conversación {conversacion_id} obtenido de Redis ({cache_key}).")
        # Doble verificación: si un cliente intenta leer una clave de propietario, bloquearlo
        if "propietario" in cache_key and (not conv or not conv.usuario or not conv.usuario.rol or conv.usuario.rol.nombre.lower() != 'administrador'):
            logger.warning(f"Seguridad: Intento de lectura de memoria cruzada bloqueado para conversación {conversacion_id}")
            return []
        return historial
    
    logger.info(f"[CACHE MISS] Historial de conversación no encontrado en Redis. Cargando de DB...")
    
    # Cargar desde SQL
    mensajes_db = list(Mensaje.objects.filter(conversacion_id=conversacion_id).order_by('-created_at')[:max_mensajes])
    mensajes_db.reverse()
    
    historial = []
    for msg in mensajes_db:
        # Filtrar información sensible de registros antiguos por seguridad
        cleaned_content = filtrar_contenido_sensible(msg.content)
        historial.append({"role": msg.role, "content": cleaned_content})
    
    # Guardar en Redis
    cache.set(cache_key, historial, timeout=ttl)
    return historial

def registrar_mensaje_y_actualizar_cache(conversacion_id: str, role: str, content: str, max_mensajes: int = 5):
    """
    Registra el nuevo mensaje (filtrado) en la base de datos SQL
    y actualiza la caché en Redis bajo el namespace correspondiente.
    """
    # Filtrar cualquier información sensible antes de persistir
    cleaned_content = filtrar_contenido_sensible(content)
    
    # 1. Guardar en SQL
    Mensaje.objects.create(conversacion_id=conversacion_id, role=role, content=cleaned_content)
    
    # 2. Actualizar caché de Redis
    cache_key, ttl, conv = resolver_conversacion_cache_key_y_ttl(conversacion_id)
    historial = cache.get(cache_key)
    
    if historial is None:
        obtener_historial_conversacion(conversacion_id, max_mensajes)
    else:
        historial.append({"role": role, "content": cleaned_content})
        if len(historial) > max_mensajes:
            historial = historial[-max_mensajes:]
        cache.set(cache_key, historial, timeout=ttl)
        logger.info(f"[CACHE UPDATE] Mensaje de '{role}' agregado al historial en Redis para conversación {conversacion_id} ({cache_key}).")
