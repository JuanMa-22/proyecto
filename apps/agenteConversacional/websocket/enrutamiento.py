from django.urls import re_path
from . import consumidores

websocket_urlpatterns = [
    re_path(r'^ws/agente-conversacional/$', consumidores.AgenteConversacionalConsumer.as_asgi()),
]
