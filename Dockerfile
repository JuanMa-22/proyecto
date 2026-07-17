# Usar una imagen oficial de Python ligera
FROM python:3.11-slim

# Evitar que Python escriba archivos .pyc en el disco
ENV PYTHONDONTWRITEBYTECODE 1
# Evitar que Python almacene en búfer stdout y stderr
ENV PYTHONUNBUFFERED 1

# Instalar dependencias del sistema necesarias
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Establecer el directorio de trabajo
WORKDIR /app

# Instalar las dependencias de Python
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Descargar el modelo de sentence-transformers durante el build
# para evitar latencias o fallos de red en el primer arranque de producción
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Copiar el código del proyecto
COPY . /app/

# Dar permisos de ejecución al script de arranque
RUN chmod +x /app/start.sh

# Exponer el puerto por defecto
EXPOSE 8000

# Arrancar usando el script que levanta Celery y Daphne
CMD ["/app/start.sh"]
