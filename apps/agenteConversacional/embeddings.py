import logging
from django.conf import settings
from apps.productoEspecificacion.models import ProductoEspecificacion

logger = logging.getLogger(__name__)

import threading

class EmbeddingsGenerator:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(EmbeddingsGenerator, cls).__new__(cls, *args, **kwargs)
                    cls._instance._model = None
        return cls._instance

    @property
    def model(self):
        """Carga perezosa del modelo con sincronización de hilos para evitar inicializaciones concurrentes."""
        if self._model is None:
            with self._lock:
                if self._model is None:
                    logger.info("Cargando modelo SentenceTransformer all-MiniLM-L6-v2...")
                    # Carga el modelo de forma perezosa para evitar imports pesados en el arranque
                    from sentence_transformers import SentenceTransformer
                    self._model = SentenceTransformer('all-MiniLM-L6-v2')
                    logger.info("Modelo SentenceTransformer cargado correctamente.")
        return self._model

    def generar_embedding(self, texto: str):
        """Genera el embedding (lista de floats) para el texto proporcionado, usando caché Redis."""
        if not texto:
            return [0.0] * 384

        import hashlib
        import time
        import urllib.request
        import urllib.error
        import json
        from django.core.cache import cache
        from decouple import config

        # Generar clave de caché para el embedding
        texto_norm = texto.strip().lower()
        texto_hash = hashlib.md5(texto_norm.encode('utf-8')).hexdigest()
        cache_key = f"emb:{texto_hash}"

        # Intentar recuperar de la caché
        cached_emb = cache.get(cache_key)
        if cached_emb is not None:
            logger.info("[CACHE HIT] Embedding recuperado de caché.")
            return cached_emb

        # 1. Intentar obtener el embedding usando la API de inferencia de Hugging Face
        # Esto consume 0 MB de RAM y es perfecto para servidores gratuitos
        for attempt in range(3):
            try:
                logger.info(f"Intentando obtener embedding desde Hugging Face API (intento {attempt + 1})...")
                api_url = "https://api-inference.huggingface.co/pipeline/feature-extraction/sentence-transformers/all-MiniLM-L6-v2"
                
                req = urllib.request.Request(
                    api_url,
                    data=json.dumps({"inputs": texto}).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                hf_token = config('HF_TOKEN', default=None)
                if hf_token:
                    req.add_header("Authorization", f"Bearer {hf_token}")
                    
                with urllib.request.urlopen(req, timeout=5) as response:
                    emb_list = json.loads(response.read().decode("utf-8"))
                    if isinstance(emb_list, list) and len(emb_list) > 0:
                        if isinstance(emb_list[0], list):
                            emb_list = emb_list[0]
                        if len(emb_list) == 384:
                            logger.info("Embedding obtenido exitosamente desde Hugging Face API.")
                            cache.set(cache_key, emb_list, timeout=86400)
                            return emb_list
                break
            except urllib.error.HTTPError as he:
                # Si el modelo se está cargando (status 503), esperar 2 segundos y reintentar
                if he.code == 503:
                    try:
                        err_data = json.loads(he.read().decode("utf-8"))
                        if "loading" in err_data.get("error", ""):
                            est_time = err_data.get("estimated_time", 2.0)
                            logger.info(f"El modelo de Hugging Face se está cargando en la API. Esperando {est_time:.1f}s antes de reintentar...")
                            time.sleep(min(est_time, 3.0))
                            continue
                    except Exception:
                        pass
                logger.warning(f"Error HTTP en Hugging Face API: {he.code}. Usando fallback...")
                break
            except Exception as e:
                logger.error(f"Error de red en Hugging Face API: {e}. Usando fallback...")
                break

        # 2. Fallback: Generar embedding localmente (puede consumir bastante memoria)
        logger.info("Usando fallback de SentenceTransformer local...")
        t_start = time.perf_counter()
        embedding = self.model.encode(texto, convert_to_numpy=True)
        emb_list = embedding.tolist()
        t_duration = time.perf_counter() - t_start

        logger.info(f"[PERF] Inferencia de SentenceTransformer local completada en {t_duration:.4f}s")

        # Guardar en caché por 24 horas (86400 segundos)
        cache.set(cache_key, emb_list, timeout=86400)
        return emb_list

    @staticmethod
    def generar_texto_producto(producto) -> str:
        """
        Concatena y formatea de forma estructurada toda la información del producto
        y sus especificaciones técnicas para que sea indexado vectorialmente.
        """
        texto_partes = [
            f"Producto: {producto.nombre}",
            f"Descripción: {producto.descripcion or 'Sin descripción'}",
            f"Precio: {producto.precio_actual} BS / {producto.precio_usd} USD",
            f"Stock disponible: {producto.stock} unidades",
            f"Categoría: {producto.categoria.nombre}",
            f"Marca: {producto.marca.nombre}"
        ]

        # Agregar especificaciones técnicas si existen
        try:
            specs = ProductoEspecificacion.objects.filter(producto=producto, estado=True).first()
            if specs:
                specs_list = []
                if specs.socket:
                    specs_list.append(f"Socket: {specs.socket}")
                if specs.chipset:
                    specs_list.append(f"Chipset: {specs.chipset}")
                if specs.tipo_ram:
                    specs_list.append(f"Tipo de RAM compatible: {specs.tipo_ram}")
                if specs.vram:
                    specs_list.append(f"VRAM: {specs.vram}")
                if specs.watts:
                    specs_list.append(f"Consumo de energía (Watts): {specs.watts}W")
                if specs.velocidad_ram:
                    specs_list.append(f"Velocidad de RAM: {specs.velocidad_ram}")
                if specs.almacenamiento:
                    specs_list.append(f"Almacenamiento: {specs.almacenamiento}")
                if specs.pci:
                    specs_list.append(f"Interfaz PCI: {specs.pci}")
                
                if specs_list:
                    texto_partes.append("Especificaciones Técnicas: " + ", ".join(specs_list))
        except Exception as e:
            logger.error(f"Error obteniendo especificaciones para producto {producto.nombre}: {e}")

        # Retornar el bloque de texto consolidado
        return "\n".join(texto_partes)
