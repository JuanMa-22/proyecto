"""
ASGI config for config project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django_asgi_app = get_asgi_application()

# Se importan los ruteadores y middlewares de channels después de get_asgi_application()
# para asegurar que Django esté completamente cargado.
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.sessions import SessionMiddlewareStack
from django.contrib.staticfiles.handlers import ASGIStaticFilesHandler
from django.conf import settings
import apps.agenteConversacional.websocket.enrutamiento

# En desarrollo (DEBUG=True), usamos ASGIStaticFilesHandler para que Daphne sirva archivos estáticos
http_handler = ASGIStaticFilesHandler(django_asgi_app) if settings.DEBUG else django_asgi_app

application = ProtocolTypeRouter({
    "http": http_handler,
    "websocket": SessionMiddlewareStack(
        AuthMiddlewareStack(
            URLRouter(
                apps.agenteConversacional.websocket.enrutamiento.websocket_urlpatterns
            )
        )
    ),
})
