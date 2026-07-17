import logging
from pgvector.django import CosineDistance
from .models import ProductoEmbedding
from .embeddings import EmbeddingsGenerator

logger = logging.getLogger(__name__)

def buscar_productos_similares(query: str, top_k: int = 5):
    """
    Realiza una búsqueda semántica de productos utilizando pgvector y CosineDistance.
    Retorna una lista de diccionarios de productos con su texto y puntaje de similitud aproximado.
    """
    import time
    from django.core.cache import cache

    t_total_start = time.perf_counter()

    # Sanitizar query para la clave de caché
    query_clean = query.strip().lower()
    cache_key = f"rag_search:{query_clean}:{top_k}"

    # Medir tiempo de consulta a Redis
    t_redis_start = time.perf_counter()
    cached_results = cache.get(cache_key)
    t_redis_duration = time.perf_counter() - t_redis_start

    if cached_results is not None:
        t_total_duration = time.perf_counter() - t_total_start
        alert_str = " [ALERT > 100ms]" if t_total_duration > 0.1 else ""
        logger.info(
            f"[PERF] RAG Búsqueda (Cache Hit) - "
            f"Tiempo Redis: {t_redis_duration:.4f}s | "
            f"Tiempo total: {t_total_duration:.4f}s{alert_str}"
        )
        return cached_results

    try:
        # 1. Generar embedding para la consulta (aprovechando caché interna de embeddings)
        t_emb_start = time.perf_counter()
        generator = EmbeddingsGenerator()
        query_vector = generator.generar_embedding(query)
        t_emb_duration = time.perf_counter() - t_emb_start

        # 2. Buscar en la base de datos usando distancia coseno filtrando activos en SQL
        t_db_start = time.perf_counter()
        resultados = ProductoEmbedding.objects.filter(producto__estado=True).annotate(
            distancia=CosineDistance('vector', query_vector)
        ).select_related('producto', 'producto__categoria', 'producto__marca').order_by('distancia')[:top_k]

        # Forzar evaluación de la query evaluando la lista
        resultados_list = list(resultados)
        t_db_duration = time.perf_counter() - t_db_start

        productos_retornados = []
        for res in resultados_list:
            prod = res.producto
            similitud = 1.0 - float(res.distancia) if res.distancia is not None else 0.0
            
            productos_retornados.append({
                "id_producto": str(prod.id_producto),
                "nombre": prod.nombre,
                "descripcion": prod.descripcion,
                "precio_actual": float(prod.precio_actual),
                "precio_usd": float(prod.precio_usd),
                "stock": prod.stock,
                "categoria": prod.categoria.nombre,
                "marca": prod.marca.nombre,
                "texto_completo": res.texto,
                "similitud": similitud
            })

        t_total_duration = time.perf_counter() - t_total_start
        
        # Evaluar tiempos mayores a 100ms
        emb_alert = " [ALERT > 100ms]" if t_emb_duration > 0.1 else ""
        db_alert = " [ALERT > 100ms]" if t_db_duration > 0.1 else ""
        total_alert = " [ALERT > 100ms]" if t_total_duration > 0.1 else ""

        logger.info(
            f"[PERF] RAG Búsqueda - "
            f"Tiempo Redis: {t_redis_duration:.4f}s | "
            f"Tiempo Embeddings: {t_emb_duration:.4f}s{emb_alert} | "
            f"Tiempo pgvector DB: {t_db_duration:.4f}s{db_alert} | "
            f"Tiempo total: {t_total_duration:.4f}s{total_alert}"
        )

        # Cachear resultados de búsqueda por 5 minutos (300 segundos)
        cache.set(cache_key, productos_retornados, timeout=300)
        return productos_retornados
    except Exception as e:
        logger.error(f"Error realizando búsqueda vectorial de productos: {e}")
        return []
