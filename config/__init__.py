# Este import asegura que la aplicación se cargue siempre
# que Django inicie para que shared_task use esta app.
from .celery import app as celery_app

__all__ = ('celery_app',)
