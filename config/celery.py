import os
from celery import Celery

# Establecer las variables de entorno de Django por defecto para Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('sismeing_chatbot')

# Usar una cadena aquí significa que el worker no tendrá que serializar
# el objeto de configuración a procesos hijo.
# - namespace='CELERY' significa que todas las claves de configuración de Celery
#   deben tener el prefijo `CELERY_` en los settings de Django.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Descubrir automáticamente tareas asíncronas en todas las aplicaciones registradas de Django.
app.autodiscover_tasks()
