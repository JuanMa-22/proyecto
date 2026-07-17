import time
from django.conf import settings
from django.http import JsonResponse
import redis
import logging

logger = logging.getLogger(__name__)

# Inicializar cliente Redis usando la URL de settings
redis_url = getattr(settings, 'REDIS_URL', 'redis://localhost:6379/0')
redis_client = redis.from_url(redis_url)

class AgenteConversacionalLimiteTasaMiddleware:
    """
    Middleware para limitar la tasa de peticiones al Agente Conversacional
    usando una ventana deslizante (sliding window) en Redis según el rol del usuario.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Solo aplicar a las rutas del agente conversacional
        if request.path.startswith('/agente-conversacional/'):
            # Evitar rate limiting para peticiones de assets o estáticos si las hubiera
            if '.' in request.path.split('/')[-1]:
                return self.get_response(request)

            # Identificar al usuario por session_id o por su IP
            usuario_id = request.session.get('usuario_id')
            es_propietario = False
            
            if usuario_id:
                try:
                    from apps.usuario.models import Usuario
                    usuario = Usuario.objects.select_related('rol').get(pk=usuario_id)
                    if usuario.estado and usuario.rol and usuario.rol.nombre.lower() == 'administrador':
                        es_propietario = True
                except Exception:
                    pass

            identificador = usuario_id or request.session.session_key or self.get_client_ip(request)
            
            if not self.verificar_rate_limit_rol(identificador, es_propietario):
                return JsonResponse(
                    {
                        "error": "Too Many Requests", 
                        "message": "Has realizado varias consultas en poco tiempo. Inténtalo nuevamente dentro de unos minutos."
                    },
                    status=429
                )
        return self.get_response(request)

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    @staticmethod
    def verificar_rate_limit(identificador, limite, periodo=60):
        """
        Verificación clásica (mantenida por retrocompatibilidad).
        """
        key = f"ratelimit:agente:{identificador}"
        ahora = time.time()
        try:
            pipe = redis_client.pipeline()
            pipe.zremrangebyscore(key, 0, ahora - periodo)
            pipe.zadd(key, {str(ahora): ahora})
            pipe.zcard(key)
            pipe.expire(key, periodo)
            resultados = pipe.execute()
            return resultados[2] <= limite
        except redis.RedisError:
            return True

    @staticmethod
    def verificar_rate_limit_rol(identificador, es_propietario):
        """
        Verifica el límite de peticiones según el rol (CLIENTE vs PROPIETARIO) 
        en una ventana de 10 minutos (600 segundos).
        """
        if es_propietario:
            # PROPIETARIO: 60 consultas cada 10 minutos
            limite = 60
            key = f"rate_limit:propietario:{identificador}"
        else:
            # CLIENTE: 20 consultas cada 10 minutos
            limite = 20
            key = f"rate_limit:cliente:{identificador}"

        periodo = 600
        ahora = time.time()
        
        try:
            pipe = redis_client.pipeline()
            pipe.zremrangebyscore(key, 0, ahora - periodo)
            pipe.zadd(key, {str(ahora): ahora})
            pipe.zcard(key)
            pipe.expire(key, periodo)
            
            resultados = pipe.execute()
            cantidad_peticiones = resultados[2]
            
            return cantidad_peticiones <= limite
        except redis.RedisError:
            # En caso de falla en Redis, permitimos la petición por resiliencia
            return True
