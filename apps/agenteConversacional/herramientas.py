import logging
from django.db.models import F, Sum, Count, Avg, Max, Min, Q
from apps.producto.models import Producto
from apps.inventario.models import Inventario
from apps.venta.models import Venta
from apps.detalleVenta.models import DetalleVenta
from apps.categoria.models import Categoria
from apps.marca.models import Marca
from apps.cliente.models import Cliente
from apps.proveedor.models import Proveedor
from apps.compra.models import Compra
from apps.detalleCompra.models import DetalleCompra
from apps.movimiento.models import Movimiento
from apps.tipoMovimiento.models import tipoMovimiento as TipoMovimiento
from apps.lote.models import LoteProducto, LoteConsumo
from apps.tipoCambio.models import TipoCambio
from apps.usuario.models import Usuario
from apps.rol.models import Rol
from apps.historialPrecio.models import HistorialPrecio
from .recuperacion_semantica import buscar_productos_similares
from .armado_pc import verificar_compatibilidad_pc, recomendar_componentes_compatibles
from django.utils import timezone
from datetime import timedelta
import uuid

logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────
# LISTAS BLANCAS DE SEGURIDAD (BACKEND DJANGO)
# ────────────────────────────────────────────────────────

TOOLS_CLIENTE = {
    "buscar_productos",
    "contar_productos",
    "verificar_compatibilidad",
    "recomendar_componente_compatible",
}

TOOLS_PROPIETARIO = {
    "buscar_productos",
    "contar_productos",
    "verificar_compatibilidad",
    "recomendar_componente_compatible",
    "consultar_db_django",
    "obtener_ventas_periodo",
    "obtener_detalles_ventas_periodo",
    "obtener_estadisticas_ventas",
    "obtener_kardex_producto",
    "obtener_stock_bajo",
}

MODEL_MAP = {
    "Producto": Producto,
    "Categoria": Categoria,
    "Marca": Marca,
    "Cliente": Cliente,
    "Proveedor": Proveedor,
    "Venta": Venta,
    "DetalleVenta": DetalleVenta,
    "Compra": Compra,
    "DetalleCompra": DetalleCompra,
    "Movimiento": Movimiento,
    "TipoMovimiento": TipoMovimiento,
    "LoteProducto": LoteProducto,
    "LoteConsumo": LoteConsumo,
    "TipoCambio": TipoCambio,
    "Usuario": Usuario,
    "HistorialPrecio": HistorialPrecio,
}

MODELOS_PERMITIDOS = set(MODEL_MAP.keys())

CAMPOS_PERMITIDOS = {
    "Producto": {
        "id_producto", "nombre", "descripcion", "precio_actual", "precio_usd", 
        "stock", "estado", "created_at", "updated_at"
    },
    "Categoria": {
        "id_categoria", "nombre", "descripcion", "estado", "created_at"
    },
    "Marca": {
        "id_marca", "nombre", "estado", "created_at"
    },
    "Cliente": {
        "id_cliente", "nombre", "nit_ci", "telefono", "direccion", "estado", "created_at"
    },
    "Proveedor": {
        "id_proveedor", "nombre", "nit", "nombre_contacto", "telefono", "estado", "created_at"
    },
    "Venta": {
        "id_venta", "fecha", "total", "estado", "created_at"
    },
    "DetalleVenta": {
        "id_detalle_venta", "venta_id", "producto_id", "cantidad", "precio_venta", "subtotal", "estado"
    },
    "Compra": {
        "id_compra", "fecha", "total", "estado", "created_at", "tipo_cambio_valor"
    },
    "DetalleCompra": {
        "id_detalle_compra", "compra_id", "producto_id", "cantidad", "precio_compra", "subtotal", "estado"
    },
    "Movimiento": {
        "id_movimiento", "producto_id", "tipoMovimiento_id", "cantidad", "stock_anterior", "stock_actual", "motivo", "fecha", "estado"
    },
    "TipoMovimiento": {
        "id_tipo_movimiento", "nombre", "estado"
    },
    "LoteProducto": {
        "id_lote", "compra_id", "producto_id", "cantidad_inicial", "cantidad_actual", "fecha_ingreso", "estado"
    },
    "LoteConsumo": {
        "id_lote_consumo", "lote_id", "venta_id", "cantidad", "fecha_consumo", "estado"
    },
    "TipoCambio": {
        "id_tipo_cambio", "fecha", "valor", "estado"
    },
    "HistorialPrecio": {
        "id_historial", "producto_id", "precio_anterior", "precio_nuevo", "fecha", "estado"
    },
    "Usuario": {
        "id_usuario", "nombre", "apellido", "email", "telefono", "direccion", "ci", "usuario", "rol_id", "estado", "created_at"
    }
}

CAMPOS_SENSIBLES = {
    "password",
    "password_hash",
    "secret_key",
    "api_key",
    "token",
    "session_key",
    "access_token",
    "refresh_token",
    "last_login",
}

RELACIONES_PERMITIDAS = {
    "Producto": {
        "categoria__nombre",
        "marca__nombre",
    },
    "Venta": {
        "cliente__nombre",
        "cliente__nit_ci",
        "usuario__usuario",
        "usuario__nombre",
    },
    "DetalleVenta": {
        "venta__total",
        "venta__fecha",
        "producto__nombre",
        "producto__categoria__nombre",
    },
    "Compra": {
        "proveedor__nombre",
    },
    "DetalleCompra": {
        "compra__total",
        "compra__fecha",
        "producto__nombre",
    },
    "Movimiento": {
        "producto__nombre",
        "tipoMovimiento__nombre",
    },
    "LoteProducto": {
        "producto__nombre",
        "compra__total",
    },
    "LoteConsumo": {
        "lote__producto__nombre",
        "venta__total",
    },
    "Usuario": {
        "rol__nombre",
    }
}

OPERACIONES_PERMITIDAS = {
    "listar",
    "obtener",
    "contar",
    "sumar",
    "promedio",
    "maximo",
    "minimo",
}

LOOKUPS_PERMITIDOS = {
    "exact",
    "iexact",
    "contains",
    "icontains",
    "gt",
    "gte",
    "lt",
    "lte",
    "date",
    "year",
    "month",
    "day",
    "range",
    "in",
}

def puede_usar_herramienta(rol: str, nombre_herramienta: str) -> bool:
    herramientas_por_rol = {
        "CLIENTE": TOOLS_CLIENTE,
        "PROPIETARIO": TOOLS_PROPIETARIO,
    }
    return nombre_herramienta in herramientas_por_rol.get(rol, set())

def es_filtro_valido(modelo_nombre: str, filtro_key: str) -> bool:
    parts = filtro_key.split("__")
    if len(parts) == 1:
        field = parts[0]
        if field in CAMPOS_SENSIBLES:
            return False
        return field in CAMPOS_PERMITIDOS.get(modelo_nombre, set())
        
    if len(parts) == 2:
        p0, p1 = parts[0], parts[1]
        if p0 in CAMPOS_SENSIBLES or p1 in CAMPOS_SENSIBLES:
            return False
        if p0 in CAMPOS_PERMITIDOS.get(modelo_nombre, set()) and p1 in LOOKUPS_PERMITIDOS:
            return True
        full_relation_field = f"{p0}__{p1}"
        if full_relation_field in RELACIONES_PERMITIDAS.get(modelo_nombre, {}):
            return True
        return False
        
    if len(parts) == 3:
        p0, p1, p2 = parts[0], parts[1], parts[2]
        if p0 in CAMPOS_SENSIBLES or p1 in CAMPOS_SENSIBLES or p2 in CAMPOS_SENSIBLES:
            return False
        full_relation_field = f"{p0}__{p1}"
        if full_relation_field in RELACIONES_PERMITIDAS.get(modelo_nombre, {}) and p2 in LOOKUPS_PERMITIDOS:
            return True
        return False
        
    return False

def parsear_valor_filtro(model_class, field_path, valor):
    try:
        parts = field_path.split("__")
        if len(parts) > 1 and parts[-1] in LOOKUPS_PERMITIDOS:
            field_name_parts = parts[:-1]
        else:
            field_name_parts = parts
            
        current_model = model_class
        field_obj = None
        for p in field_name_parts:
            # Manejar sufijos de llaves foráneas implícitas en Django ORM (ej. rol_id)
            clean_p = p
            if p.endswith('_id') and not hasattr(current_model, p):
                clean_p = p[:-3]
            field_obj = current_model._meta.get_field(clean_p)
            if field_obj.is_relation:
                current_model = field_obj.related_model
                
        from django.db import models
        if isinstance(field_obj, (models.IntegerField, models.AutoField, models.BigIntegerField, models.SmallIntegerField)):
            return int(valor)
        elif isinstance(field_obj, (models.FloatField, models.DecimalField)):
            return float(valor)
        elif isinstance(field_obj, models.BooleanField):
            if isinstance(valor, str):
                return valor.lower() in ['true', '1', 'yes', 't']
            return bool(valor)
        elif isinstance(field_obj, models.UUIDField):
            return uuid.UUID(str(valor))
    except Exception as e:
        logger.warning(f"Error resolviendo tipo para campo {field_path} con valor {valor}: {e}")
        
    return valor

# ────────────────────────────────────────────────────────
# IMPLEMENTACIÓN DE LAS FUNCIONES DE LAS HERRAMIENTAS
# ────────────────────────────────────────────────────────

def tool_buscar_productos(query: str):
    logger.info(f"Ejecutando herramienta: buscar_productos con query='{query}'")
    return buscar_productos_similares(query, top_k=3)

def tool_verificar_compatibilidad(productos_ids: list):
    logger.info(f"Ejecutando herramienta: verificar_compatibilidad con {len(productos_ids)} productos")
    try:
        return verificar_compatibilidad_pc(productos_ids)
    except Exception as e:
        logger.error(f"Error en tool_verificar_compatibilidad: {e}")
        return {"error": str(e), "compatible": False, "mensajes": ["Ocurrió un error al verificar compatibilidad."]}

def tool_recomendar_componente_compatible(componentes_actuales_ids: list, categoria_objetivo: str):
    logger.info(f"Ejecutando herramienta: recomendar_componente_compatible para '{categoria_objetivo}'")
    try:
        return recomendar_componentes_compatibles(componentes_actuales_ids, categoria_objetivo)
    except Exception as e:
        logger.error(f"Error en tool_recomendar_componente_compatible: {e}")
        return []

def tool_obtener_stock_bajo(limite_maximo: int = None):
    from django.core.cache import cache
    cache_key = f"tool_stock_bajo:{limite_maximo}"
    cached_val = cache.get(cache_key)
    if cached_val is not None:
        logger.info(f"[CACHE HIT] obtener_stock_bajo con limite_maximo={limite_maximo}")
        return cached_val

    logger.info(f"Ejecutando herramienta: obtener_stock_bajo con limite_maximo={limite_maximo}")
    try:
        if limite_maximo is not None:
            productos = Producto.objects.filter(
                estado=True,
                stock__lte=limite_maximo
            ).select_related('categoria', 'marca', 'inventario')
            
            resultado = []
            for prod in productos:
                stock_min = prod.inventario.stock_minimo if hasattr(prod, 'inventario') and prod.inventario else 5
                resultado.append({
                    "nombre": prod.nombre,
                    "stock_actual": prod.stock,
                    "stock_minimo": stock_min,
                    "categoria": prod.categoria.nombre,
                    "marca": prod.marca.nombre,
                    "precio_bs": float(prod.precio_actual),
                    "imagen_url": prod.imagen.url if prod.imagen else None
                })
            cache.set(cache_key, resultado, timeout=60)
            return resultado

        productos = Producto.objects.filter(estado=True).select_related('categoria', 'marca', 'inventario').filter(
            Q(inventario__isnull=False, stock__lte=F('inventario__stock_minimo')) |
            Q(inventario__isnull=True, stock__lte=5)
        )
        
        resultado = []
        for prod in productos:
            stock_min = prod.inventario.stock_minimo if hasattr(prod, 'inventario') and prod.inventario else 5
            resultado.append({
                "nombre": prod.nombre,
                "stock_actual": prod.stock,
                "stock_minimo": stock_min,
                "categoria": prod.categoria.nombre,
                "marca": prod.marca.nombre,
                "precio_bs": float(prod.precio_actual),
                "imagen_url": prod.imagen.url if prod.imagen else None
            })
            
        cache.set(cache_key, resultado, timeout=60)
        return resultado
    except Exception as e:
        logger.error(f"Error en tool_obtener_stock_bajo: {e}")
        return {"error": str(e)}

def tool_contar_productos(marca: str = None, categoria: str = None, producto_nombre: str = None,
                          stock_maximo: int = None, stock_minimo: int = None,
                          precio_maximo: float = None, precio_minimo: float = None,
                          limite_maximo: int = None):
    if limite_maximo is not None and stock_maximo is None:
        stock_maximo = limite_maximo

    # Casteo seguro de parámetros numéricos que pueden llegar como string
    if stock_maximo is not None:
        try:
            stock_maximo = int(stock_maximo)
        except (ValueError, TypeError):
            stock_maximo = None
            
    if stock_minimo is not None:
        try:
            stock_minimo = int(stock_minimo)
        except (ValueError, TypeError):
            stock_minimo = None
            
    if precio_maximo is not None:
        try:
            precio_maximo = float(precio_maximo)
        except (ValueError, TypeError):
            precio_maximo = None
            
    if precio_minimo is not None:
        try:
            precio_minimo = float(precio_minimo)
        except (ValueError, TypeError):
            precio_minimo = None

    if categoria:
        cat_clean = categoria.lower().strip()
        if "video" in cat_clean or "grafica" in cat_clean or "gráfica" in cat_clean:
            categoria = "Tarjeta de Video"
        elif "procesador" in cat_clean or "cpu" in cat_clean:
            categoria = "Procesador"
        elif "memoria" in cat_clean or "ram" in cat_clean:
            categoria = "Memoria RAM"
        elif "ssd" in cat_clean:
            categoria = "SSD"
        elif "disco" in cat_clean or "duro" in cat_clean or "hdd" in cat_clean:
            categoria = "Disco Duro"
        elif "almacenamiento" in cat_clean:
            categoria = "SSD"
        elif "placa" in cat_clean or "motherboard" in cat_clean or "mainboard" in cat_clean:
            categoria = "Placa Madre"
        elif "fuente" in cat_clean or "poder" in cat_clean or "psu" in cat_clean:
            categoria = "Fuente de Poder"
        elif "gabinete" in cat_clean or "case" in cat_clean or "chasis" in cat_clean:
            categoria = "Gabinete"
        elif "monitor" in cat_clean or "pantalla" in cat_clean:
            categoria = "Monitor"
        elif "periferico" in cat_clean or "periférico" in cat_clean or "teclado" in cat_clean or "mouse" in cat_clean or "auricular" in cat_clean:
            categoria = "Perifericos"

    from django.core.cache import cache
    cache_key = f"tool_contar_productos:{marca}:{categoria}:{producto_nombre}:{stock_maximo}:{stock_minimo}:{precio_maximo}:{precio_minimo}"
    cached_val = cache.get(cache_key)
    if cached_val is not None:
        logger.info(f"[CACHE HIT] contar_productos")
        return cached_val

    logger.info(f"Ejecutando herramienta: contar_productos")
    try:
        queryset = Producto.objects.filter(estado=True).select_related('categoria', 'marca')
        if marca:
            queryset = queryset.filter(marca__nombre__icontains=marca)
        if categoria:
            queryset = queryset.filter(categoria__nombre__icontains=categoria)
        if producto_nombre:
            queryset = queryset.filter(nombre__icontains=producto_nombre)
        if stock_maximo is not None:
            queryset = queryset.filter(stock__lte=stock_maximo)
        if stock_minimo is not None:
            queryset = queryset.filter(stock__gte=stock_minimo)
        if precio_maximo is not None:
            queryset = queryset.filter(precio_actual__lte=precio_maximo)
        if precio_minimo is not None:
            queryset = queryset.filter(precio_actual__gte=precio_minimo)
            
        agregado = queryset.aggregate(
            total_count=Count('id_producto'),
            total_stock=Sum('stock')
        )
        total = agregado['total_count'] or 0
        total_stock = agregado['total_stock'] or 0
        
        detalles = []
        if total <= 100:
            for p in queryset:
                detalles.append({
                    "nombre": p.nombre,
                    "stock": p.stock,
                    "precio_bs": float(p.precio_actual),
                    "categoria": p.categoria.nombre,
                    "marca": p.marca.nombre,
                    "imagen_url": p.imagen.url if p.imagen else None
                })
                
        resultado = {
            "cantidad_total": total,
            "unidades_stock_total": total_stock,
            "detalles_productos": detalles,
            "filtros_aplicados": {
                "marca": marca,
                "categoria": categoria,
                "producto_nombre": producto_nombre,
                "stock_maximo": stock_maximo,
                "stock_minimo": stock_minimo,
                "precio_maximo": precio_maximo,
                "precio_minimo": precio_minimo
            }
        }
        cache.set(cache_key, resultado, timeout=60)
        return resultado
    except Exception as e:
        logger.error(f"Error en tool_contar_productos: {e}")
        return {"error": str(e)}

def tool_obtener_ventas_periodo(dia: int = None, mes: int = None, ano: int = None):
    from django.core.cache import cache
    cache_key = f"tool_ventas_periodo:{dia}:{mes}:{ano}"
    cached_val = cache.get(cache_key)
    if cached_val is not None:
        logger.info(f"[CACHE HIT] obtener_ventas_periodo")
        return cached_val

    logger.info(f"Ejecutando herramienta: obtener_ventas_periodo con dia={dia}, mes={mes}, ano={ano}")
    try:
        queryset = Venta.objects.filter(estado=True)
        if ano:
            queryset = queryset.filter(fecha__year=ano)
        if mes:
            queryset = queryset.filter(fecha__month=mes)
        if dia:
            queryset = queryset.filter(fecha__day=dia)
            
        agregado = queryset.aggregate(
            total=Sum('total'),
            cantidad=Count('id_venta')
        )
        
        total_bs = float(agregado['total'] or 0.0)
        cantidad_ventas = agregado['cantidad'] or 0
        
        resultado = {
            "total_ventas_recaudado_bs": total_bs,
            "cantidad_de_ventas": cantidad_ventas,
            "periodo": {"dia": dia, "mes": mes, "ano": ano}
        }
        cache.set(cache_key, resultado, timeout=60)
        return resultado
    except Exception as e:
        logger.error(f"Error en tool_obtener_ventas_periodo: {e}")
        return {"error": str(e)}

def tool_obtener_detalles_ventas_periodo(dia: int = None, mes: int = None, ano: int = None):
    from django.core.cache import cache
    cache_key = f"tool_detalles_ventas_periodo:{dia}:{mes}:{ano}"
    cached_val = cache.get(cache_key)
    if cached_val is not None:
        logger.info(f"[CACHE HIT] obtener_detalles_ventas_periodo")
        return cached_val

    logger.info(f"Ejecutando herramienta: obtener_detalles_ventas_periodo")
    try:
        queryset = DetalleVenta.objects.filter(estado=True, venta__estado=True)
        if ano:
            queryset = queryset.filter(venta__fecha__year=ano)
        if mes:
            queryset = queryset.filter(venta__fecha__month=mes)
        if dia:
            queryset = queryset.filter(venta__fecha__day=dia)
            
        items = queryset.values(
            'producto__nombre', 
            'producto__marca__nombre'
        ).annotate(
            cantidad_vendida=Sum('cantidad'),
            total_bs=Sum('subtotal')
        ).order_by('-cantidad_vendida')
        
        detalles = []
        for item in items:
            detalles.append({
                "producto": item['producto__nombre'],
                "marca": item['producto__marca__nombre'],
                "cantidad_vendida": item['cantidad_vendida'],
                "subtotal_recaudado_bs": float(item['total_bs'])
            })
            
        resultado = {
            "productos_vendidos": detalles,
            "periodo": {"dia": dia, "mes": mes, "ano": ano}
        }
        cache.set(cache_key, resultado, timeout=60)
        return resultado
    except Exception as e:
        logger.error(f"Error en tool_obtener_detalles_ventas_periodo: {e}")
        return {"error": str(e)}

def tool_obtener_estadisticas_ventas(limite: int = 10):
    from django.core.cache import cache
    cache_key = f"tool_estadisticas_ventas:{limite}"
    cached_val = cache.get(cache_key)
    if cached_val is not None:
        logger.info("[CACHE HIT] obtener_estadisticas_ventas")
        return cached_val

    logger.info(f"Ejecutando herramienta: obtener_estadisticas_ventas")
    try:
        queryset = DetalleVenta.objects.filter(estado=True, venta__estado=True)
        
        productos = list(queryset.values('producto__nombre', 'producto__categoria__nombre').annotate(
            total_vendido=Sum('cantidad'),
            total_recaudado=Sum('subtotal')
        ).order_by('-total_vendido')[:limite])
        
        for p in productos:
            p['total_recaudado'] = float(p['total_recaudado'])
            
        categorias = list(queryset.values('producto__categoria__nombre').annotate(
            total_vendido=Sum('cantidad'),
            total_recaudado=Sum('subtotal')
        ).order_by('-total_recaudado'))
        
        for c in categorias:
            c['total_recaudado'] = float(c['total_recaudado'])
            
        resultado = {
            "productos_mas_vendidos": productos,
            "ventas_por_categoria": categorias
        }
        cache.set(cache_key, resultado, timeout=60)
        return resultado
    except Exception as e:
        logger.error(f"Error en tool_obtener_estadisticas_ventas: {e}")
        return {"error": str(e)}

def tool_obtener_kardex_producto(producto_nombre: str = None):
    from apps.movimiento.models import Movimiento
    from django.core.cache import cache
    cache_key = f"tool_kardex:{producto_nombre}"
    cached_val = cache.get(cache_key)
    if cached_val is not None:
        logger.info("[CACHE HIT] obtener_kardex_producto")
        return cached_val

    logger.info(f"Ejecutando herramienta: obtener_kardex_producto")
    try:
        queryset = Movimiento.objects.filter(estado=True).select_related('producto', 'tipoMovimiento')
        if producto_nombre:
            queryset = queryset.filter(producto__nombre__icontains=producto_nombre)
        
        queryset = queryset.order_by('-fecha')[:50]
        
        movimientos = []
        for m in queryset:
            movimientos.append({
                "producto": m.producto.nombre,
                "tipo_movimiento": m.tipoMovimiento.nombre,
                "cantidad": m.cantidad,
                "stock_anterior": m.stock_anterior,
                "stock_actual": m.stock_actual,
                "motivo": m.motivo,
                "fecha": m.fecha.strftime("%Y-%m-%d %H:%M:%S")
            })
            
        resultado = {
            "producto_buscado": producto_nombre,
            "cantidad_movimientos": len(movimientos),
            "movimientos": movimientos
        }
        cache.set(cache_key, resultado, timeout=30)
        return resultado
    except Exception as e:
        logger.error(f"Error en tool_obtener_kardex_producto: {e}")
        return {"error": str(e)}

# ────────────────────────────────────────────────────────
# FASES 4-11: INTÉRPRETE SEGURO ESTRUCTURADO DJANGO ORM
# ────────────────────────────────────────────────────────

def tool_consultar_db_django(modelo: str, operacion: str, filtros: dict = None, campos: list = None, orden: str = None, limite: int = None):
    """
    [Propietario] Intérprete seguro de consultas Django ORM.
    Recibe parámetros estructurados en JSON y ejecuta consultas de solo lectura,
    validando modelos, campos, relaciones, operaciones y lookups contra listas blancas en Python.
    """
    logger.info(f"Seguridad DB: Consulta estructurada para modelo={modelo}, operacion={operacion}")
    
    # 1. Validar Modelo
    if modelo not in MODELOS_PERMITIDOS:
        return {"error": f"Consulta rechazada: el modelo '{modelo}' no está en la lista blanca."}
        
    model_class = MODEL_MAP[modelo]
    
    # 2. Validar Operación
    if operacion not in OPERACIONES_PERMITIDAS:
        return {"error": f"Consulta rechazada: la operación '{operacion}' no está permitida en consultas."}
        
    # 3. Validar y procesar Filtros
    processed_filters = {}
    hoy = timezone.now().date()
    
    if filtros:
        for k, v in filtros.items():
            # Impedir inyección a través de nombres de filtro o lookups arbitrarios
            if not es_filtro_valido(modelo, k):
                return {"error": f"Consulta rechazada: el filtro '{k}' no está permitido."}
                
            # Tratamiento de valores temporales relativos
            if isinstance(v, str):
                v_lower = v.lower().strip()
                base_field_parts = k.split("__")
                if len(base_field_parts) > 1 and base_field_parts[-1] in LOOKUPS_PERMITIDOS:
                    base_field = "__".join(base_field_parts[:-1])
                else:
                    base_field = k
                    
                if v_lower == 'hoy':
                    processed_filters[f"{base_field}__date"] = hoy
                    continue
                elif v_lower == 'ayer':
                    processed_filters[f"{base_field}__date"] = hoy - timedelta(days=1)
                    continue
                elif v_lower == 'este mes':
                    processed_filters[f"{base_field}__year"] = hoy.year
                    processed_filters[f"{base_field}__month"] = hoy.month
                    continue
                elif v_lower == 'este año':
                    processed_filters[f"{base_field}__year"] = hoy.year
                    continue
            
            # Validar y convertir tipos
            parsed_val = parsear_valor_filtro(model_class, k, v)
            processed_filters[k] = parsed_val
            
    # 4. Validar Orden
    if orden:
        clean_orden = orden.lstrip("-")
        # El campo de ordenación debe ser un campo permitido
        if clean_orden not in CAMPOS_PERMITIDOS.get(modelo, set()) and clean_orden not in RELACIONES_PERMITIDAS.get(modelo, set()):
            return {"error": f"Consulta rechazada: ordenación por '{orden}' no permitida."}

    # 5. Validar Campos a Seleccionar
    selected_fields = []
    if campos:
        for c in campos:
            if c in CAMPOS_SENSIBLES:
                return {"error": f"Consulta rechazada: acceso al campo sensible '{c}' bloqueado."}
            if c not in CAMPOS_PERMITIDOS.get(modelo, set()) and c not in RELACIONES_PERMITIDAS.get(modelo, set()):
                return {"error": f"Consulta rechazada: el campo '{c}' no está permitido."}
            selected_fields.append(c)
    else:
        # Por defecto, todos los campos permitidos del modelo
        selected_fields = list(CAMPOS_PERMITIDOS.get(modelo, set()))

    # 6. Validar y ajustar Límites
    if limite is None or limite <= 0:
        limite_val = 20
    else:
        limite_val = min(limite, 50)  # Límite absoluto 50
        
    try:
        # Construir consulta base
        queryset = model_class.objects.all()
        
        if processed_filters:
            queryset = queryset.filter(**processed_filters)
            
        if orden:
            queryset = queryset.order_by(orden)
            
        # Ejecutar operaciones
        if operacion == "contar":
            return {"resultado": queryset.count()}
            
        elif operacion in ["sumar", "promedio", "maximo", "minimo"]:
            if not campos:
                return {"error": f"Consulta rechazada: la operación '{operacion}' requiere un campo en 'campos'."}
            campo_op = campos[0]
            if campo_op not in CAMPOS_PERMITIDOS.get(modelo, set()):
                return {"error": f"Consulta rechazada: el campo '{campo_op}' no está permitido para agregación."}
                
            if operacion == "sumar":
                agg_res = queryset.aggregate(resultado=Sum(campo_op))
            elif operacion == "promedio":
                agg_res = queryset.aggregate(resultado=Avg(campo_op))
            elif operacion == "maximo":
                agg_res = queryset.aggregate(resultado=Max(campo_op))
            elif operacion == "minimo":
                agg_res = queryset.aggregate(resultado=Min(campo_op))
                
            val = agg_res.get("resultado")
            from decimal import Decimal
            if isinstance(val, Decimal):
                val = float(val)
            return {"resultado": val}
            
        elif operacion == "obtener":
            queryset = queryset.values(*selected_fields)
            res = queryset.first()
            if res:
                # Convertir UUIDs a string para serialización JSON limpia
                for k, val in res.items():
                    if isinstance(val, uuid.UUID):
                        res[k] = str(val)
            return {"resultado": res}
            
        elif operacion == "listar":
            queryset = queryset.values(*selected_fields)[:limite_val]
            records = list(queryset)
            for r in records:
                for k, val in r.items():
                    if isinstance(val, uuid.UUID):
                        r[k] = str(val)
            return {"resultado": records}
            
    except Exception as e:
        logger.error(f"Error interpretando consulta estructurada: {e}")
        return {"error": f"Excepción en base de datos: {str(e)}"}

# Mapeo de nombres a funciones en python
TOOL_REGISTRY = {
    "buscar_productos": tool_buscar_productos,
    "verificar_compatibilidad": tool_verificar_compatibilidad,
    "recomendar_componente_compatible": tool_recomendar_componente_compatible,
    "obtener_stock_bajo": tool_obtener_stock_bajo,
    "contar_productos": tool_contar_productos,
    "obtener_ventas_periodo": tool_obtener_ventas_periodo,
    "obtener_detalles_ventas_periodo": tool_obtener_detalles_ventas_periodo,
    "obtener_estadisticas_ventas": tool_obtener_estadisticas_ventas,
    "obtener_kardex_producto": tool_obtener_kardex_producto,
    "consultar_db_django": tool_consultar_db_django,
}

EJECUTOR_HERRAMIENTAS = TOOL_REGISTRY

# ────────────────────────────────────────────────────────
# DEFINICIÓN DE ESQUEMAS DE LAS HERRAMIENTAS PARA GROQ
# ────────────────────────────────────────────────────────

DEFINICION_HERRAMIENTAS_CLIENTE = [
    {
        "type": "function",
        "function": {
            "name": "buscar_productos",
            "description": (
                "Busca componentes de computadoras, procesadores, accesorios y cualquier producto en la base de datos "
                "de la tienda usando búsqueda semántica o palabras clave. Úsala SIEMPRE que el usuario pregunte "
                "por la existencia, stock, precios, marcas, categorías (como Ryzen, Intel, SSD, memorias RAM, etc.) o especificaciones de cualquier producto."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "El término de búsqueda (ej. 'procesador intel i7', 'tarjetas de video baratas')."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "verificar_compatibilidad",
            "description": (
                "Verifica la compatibilidad técnica entre un conjunto de IDs de productos seleccionados "
                "para el armado de una PC (procesador, placa madre, memoria RAM y fuente de poder). "
                "Compara sockets, tipo de RAM (DDR4 vs DDR5) y calcula el consumo en Watts estimando "
                "si la fuente tiene potencia suficiente."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "productos_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Una lista de strings representando los UUIDs de los productos a validar."
                    }
                },
                "required": ["productos_ids"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "recomendar_componente_compatible",
            "description": (
                "Recomienda componentes disponibles en stock de una categoría objetivo que sean "
                "técnicamente compatibles con los componentes ya elegidos en un armado de PC."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "componentes_actuales_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Lista de UUIDs de componentes que el usuario ya seleccionó."
                    },
                    "categoria_objetivo": {
                        "type": "string",
                        "description": "La categoría que desea agregar (ej. 'Placas Madre', 'Procesadores', 'Memorias RAM')."
                    }
                },
                "required": ["componentes_actuales_ids", "categoria_objetivo"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "contar_productos",
            "description": (
                "Obtiene la cantidad total, stock acumulado Y LA LISTA DETALLADA (nombre, stock, precio) de los productos en la tienda (hasta 100 productos). "
                "Úsale SIEMPRE que el usuario pregunte cuántos hay, el stock total, solicite LISTAR o detallar componentes, o cuando solicite filtros de stock o precio (ej. 'stock menor a 5', 'cuesta menos de 100', 'en stock', 'sin stock')."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "marca": {
                        "type": "string",
                        "description": "Nombre de la marca a filtrar (opcional, ej. 'Corsair')."
                    },
                    "categoria": {
                        "type": "string",
                        "description": "Nombre de la categoría a filtrar (opcional, ej. 'Memorias RAM')."
                    },
                    "producto_nombre": {
                        "type": "string",
                        "description": "Parte del nombre del producto a buscar (opcional)."
                    },
                    "stock_maximo": {
                        "type": ["integer", "string"],
                        "description": "Filtro opcional para obtener solo productos con stock menor o igual a este valor (ej. 4 para stock < 5)."
                    },
                    "limite_maximo": {
                        "type": ["integer", "string"],
                        "description": "Alias para stock_maximo. Filtro opcional para obtener solo productos con stock menor o igual a este valor."
                    },
                    "stock_minimo": {
                        "type": ["integer", "string"],
                        "description": "Filtro opcional para obtener solo productos con stock mayor o igual a este valor."
                    },
                    "precio_maximo": {
                        "type": ["number", "string"],
                        "description": "Filtro opcional para obtener solo productos con precio menor o igual a este valor en bolivianos."
                    },
                    "precio_minimo": {
                        "type": ["number", "string"],
                        "description": "Filtro opcional para obtener solo productos con precio mayor o igual a este valor en bolivianos."
                    }
                },
                "required": []
            }
        }
    }
]

# El Propietario tiene acceso a todas las herramientas del cliente, más las de administración
DEFINICION_HERRAMIENTAS_PROPIETARIO = DEFINICION_HERRAMIENTAS_CLIENTE + [
    {
        "type": "function",
        "function": {
            "name": "obtener_stock_bajo",
            "description": (
                "Permite al propietario saber qué productos tienen existencias bajas (stock menor o igual a "
                "su stock mínimo establecido, o menor o igual a un límite específico de unidades)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "limite_maximo": {
                        "type": "integer",
                        "description": "Filtro opcional para obtener solo productos con stock menor o igual a este valor (ej. 5)."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "obtener_ventas_periodo",
            "description": (
                "Permite al propietario obtener el total recaudado en bolivianos (BS) y la cantidad de ventas "
                "concretadas en un periodo de tiempo específico (día, mes y/o año)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "dia": {
                        "type": "integer",
                        "description": "El número del día del mes (1-31, opcional)."
                    },
                    "mes": {
                        "type": "integer",
                        "description": "El número del mes (1-12, opcional)."
                    },
                    "ano": {
                        "type": "integer",
                        "description": "El número del año de cuatro dígitos (ej. 2026, opcional)."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "obtener_detalles_ventas_periodo",
            "description": (
                "Permite al propietario conocer en detalle qué productos específicos se vendieron, "
                "en qué cantidades y cuánto dinero recaudaron en un determinado día, mes y/o año."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "dia": {
                        "type": "integer",
                        "description": "El número del día del mes (1-31, opcional)."
                    },
                    "mes": {
                        "type": "integer",
                        "description": "El número del mes (1-12, opcional)."
                    },
                    "ano": {
                        "type": "integer",
                        "description": "El número del año de cuatro dígitos (ej. 2026, opcional)."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "obtener_estadisticas_ventas",
            "description": (
                "Permite al propietario obtener estadísticas analíticas de ventas: productos más vendidos "
                "(top de ventas) y desglose de ventas totales y unidades vendidas por categoría."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "limite": {
                        "type": "integer",
                        "description": "El número de productos en el ranking a devolver (opcional, por defecto 10)."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "obtener_kardex_producto",
            "description": (
                "Permite al propietario obtener el kardex o historial de movimientos de inventario "
                "(entradas, salidas, stock anterior, stock actual, fecha, motivo) de un producto específico, "
                "o de toda la tienda si no se especifica un nombre."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "producto_nombre": {
                        "type": "string",
                        "description": "El nombre o parte del nombre del producto a consultar (opcional)."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_db_django",
            "description": (
                "Permite al propietario realizar consultas avanzadas o de propósito general a cualquier tabla de la base de datos "
                "usando un formato estructurado de solo lectura. Úsala para responder preguntas que involucren modelos que no tienen "
                "herramientas específicas (ej. usuarios, compras, proveedores, clientes, lotes, tipo de cambio, etc.)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "modelo": {
                        "type": "string",
                        "description": "Nombre del modelo a consultar. Modelos permitidos: Producto, Categoria, Marca, Cliente, Proveedor, Venta, DetalleVenta, Compra, DetalleCompra, Movimiento, TipoMovimiento, LoteProducto, LoteConsumo, TipoCambio, HistorialPrecio, Usuario."
                    },
                    "operacion": {
                        "type": "string",
                        "description": "Operación a realizar. Permitidas: 'listar', 'obtener', 'contar', 'sumar', 'promedio', 'maximo', 'minimo'."
                    },
                    "filtros": {
                        "type": "object",
                        "description": "Diccionario opcional de filtros clave-valor (ej: {'estado': True, 'precio_actual__gte': 1500}). Soporta lookups de Django y valores temporales relativos ('hoy', 'ayer', 'este mes', 'este año')."
                    },
                    "campos": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Lista de campos específicos a retornar. Ejemplo: ['nombre', 'categoria__nombre']."
                    },
                    "orden": {
                        "type": "string",
                        "description": "Campo por el cual ordenar los resultados (ej: '-created_at')."
                    },
                    "limite": {
                        "type": "integer",
                        "description": "Límite opcional de registros a retornar (máximo absoluto 50, por defecto 20)."
                    }
                },
                "required": ["modelo", "operacion"]
            }
        }
    }
]
