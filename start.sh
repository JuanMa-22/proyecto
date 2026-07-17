#!/bin/sh

# Salir inmediatamente si un comando falla
set -e

echo "=== Ejecutando Migraciones ==="
python manage.py migrate --noinput

echo "=== Recopilando Archivos Estáticos ==="
python manage.py collectstatic --noinput

echo "=== Iniciando Celery Worker en segundo plano ==="
# --concurrency=1 limita el uso de RAM a un solo proceso secundario para el plan gratuito
celery -A config worker --loglevel=info --concurrency=1 &

echo "=== Iniciando Servidor Daphne ==="
# Render asigna dinámicamente un puerto en la variable $PORT
PORT_NUM=${PORT:-8000}
exec daphne -b 0.0.0.0 -p $PORT_NUM config.asgi:application
