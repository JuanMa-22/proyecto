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

        if query_vector is None:
            # Fallback de búsqueda de texto si no se pudo obtener el embedding (API caída y local deshabilitado en prod)
            logger.warning("No se pudo obtener el vector de embedding. Ejecutando fallback de búsqueda de texto ORM...")
            from django.db.models import Q
            from apps.producto.models import Producto
            
            query_clean = query.strip()
            # 1. Intentar coincidencia exacta de la frase de búsqueda completa
            productos = list(Producto.objects.filter(nombre__icontains=query_clean, estado=True).select_related('categoria', 'marca')[:top_k])
            
            # 2. Si no hay suficientes, intentar que contenga todas las palabras clave significativas (AND)
            if len(productos) < top_k:
                palabras = [p for p in query_clean.split() if len(p) > 2]
                if palabras:
                    q_and = Q()
                    for pal in palabras:
                        q_and &= Q(nombre__icontains=pal)
                    
                    ids_existentes = [p.id_producto for p in productos]
                    productos_and = Producto.objects.filter(q_and, estado=True).exclude(id_producto__in=ids_existentes).select_related('categoria', 'marca')[:top_k - len(productos)]
                    productos.extend(productos_and)
            
            # 3. Si aún faltan, buscar por coincidencia parcial de palabras clave (OR)
            if len(productos) < top_k:
                palabras = [p for p in query_clean.split() if len(p) > 2]
                if palabras:
                    q_or = Q()
                    for pal in palabras:
                        q_or |= Q(nombre__icontains=pal)
                    
                    ids_existentes = [p.id_producto for p in productos]
                    productos_or = Producto.objects.filter(q_or, estado=True).exclude(id_producto__in=ids_existentes).select_related('categoria', 'marca')[:top_k - len(productos)]
                    productos.extend(productos_or)

            productos_retornados = []
            for prod in productos:
                productos_retornados.append({
                    "id_producto": str(prod.id_producto),
                    "nombre": prod.nombre,
                    "descripcion": prod.descripcion,
                    "precio_actual": float(prod.precio_actual),
                    "precio_usd": float(prod.precio_usd),
                    "stock": prod.stock,
                    "categoria": prod.categoria.nombre,
                    "marca": prod.marca.nombre,
                    "imagen_url": prod.imagen.url if prod.imagen else None,
                    "texto_completo": f"Producto: {prod.nombre} - {prod.descripcion or ''}",
                    "similitud": 0.85
                })
            
            t_total_duration = time.perf_counter() - t_total_start
            logger.info(f"[PERF] Búsqueda de texto de fallback completada en {t_total_duration:.4f}s")
            cache.set(cache_key, productos_retornados, timeout=300)
            return productos_retornados

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
                "imagen_url": prod.imagen.url if prod.imagen else None,
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
