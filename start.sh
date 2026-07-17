#!/bin/sh

# Salir inmediatamente si un comando falla
set -e

echo "=== Ejecutando Migraciones ==="
python manage.py migrate --noinput

if [ "$LOAD_DATA" = "True" ] || [ "$LOAD_DATA" = "true" ]; then
  echo "=== Cargando datos desde db.json ==="
  # Excluimos contenttypes y auth.Permission para prevenir colisiones en Django 5+
  python manage.py loaddata db.json --exclude contenttypes --exclude auth.Permission || echo "Advertencia: Algunos datos no pudieron ser cargados o ya existen."
fi

echo "=== Recopilando Archivos Estáticos ==="
python manage.py collectstatic --noinput

if [ "$CELERY_TASK_ALWAYS_EAGER" = "True" ] || [ "$CELERY_TASK_ALWAYS_EAGER" = "true" ]; then
  echo "=== Celery Always Eager activo: las tareas se ejecutarán síncronamente en Daphne, no se inicia worker secundario ==="
else
  echo "=== Iniciando Celery Worker en segundo plano ==="
  # --concurrency=1 limita el uso de RAM a un solo proceso secundario para el plan gratuito
  celery -A config worker --loglevel=info --concurrency=1 &
fi

echo "=== Iniciando Servidor Daphne ==="
# Render asigna dinámicamente un puerto en la variable $PORT
PORT_NUM=${PORT:-8000}
exec daphne -b 0.0.0.0 -p $PORT_NUM config.asgi:application
