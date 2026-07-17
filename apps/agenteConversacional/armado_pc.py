import logging
from decimal import Decimal
from apps.producto.models import Producto
from apps.productoEspecificacion.models import ProductoEspecificacion

logger = logging.getLogger(__name__)

def obtener_especificaciones_productos(productos_ids):
    """
    Obtiene los productos y sus especificaciones correspondientes
    a partir de una lista de IDs.
    """
    productos = Producto.objects.filter(id_producto__in=productos_ids, estado=True).select_related('categoria')
    specs = {spec.producto_id: spec for spec in ProductoEspecificacion.objects.filter(producto__in=productos, estado=True)}
    return productos, specs

def verificar_compatibilidad_pc(productos_ids):
    """
    Verifica la compatibilidad de una lista de IDs de productos.
    Retorna un diccionario detallando la compatibilidad, watts consumidos y precio total.
    """
    productos, specs = obtener_especificaciones_productos(productos_ids)
    
    # Clasificar componentes por categoría
    cpu = None
    motherboard = None
    ram = None
    gpu = None
    psu = None
    
    precio_total_bs = Decimal("0.00")
    precio_total_usd = Decimal("0.00")
    
    for prod in productos:
        cat_nombre = prod.categoria.nombre.lower()
        precio_total_bs += prod.precio_actual
        precio_total_usd += prod.precio_usd
        
        # Asignar roles clave
        if "procesador" in cat_nombre or "cpu" in cat_nombre:
            cpu = prod
        elif "placa" in cat_nombre or "motherboard" in cat_nombre:
            motherboard = prod
        elif "ram" in cat_nombre:
            ram = prod
        elif "grafica" in cat_nombre or "gpu" in cat_nombre or "video" in cat_nombre:
            gpu = prod
        elif "fuente" in cat_nombre or "psu" in cat_nombre:
            psu = prod

    compatibilidad_mensajes = []
    es_compatible = True
    
    # 1. Verificar CPU y Placa Madre (Socket)
    if cpu and motherboard:
        cpu_spec = specs.get(cpu.id_producto)
        mb_spec = specs.get(motherboard.id_producto)
        
        if cpu_spec and mb_spec:
            if cpu_spec.socket and mb_spec.socket and cpu_spec.socket.strip().lower() != mb_spec.socket.strip().lower():
                es_compatible = False
                compatibilidad_mensajes.append(
                    f"❌ Incompatibilidad de Socket: El procesador '{cpu.nombre}' usa socket '{cpu_spec.socket}' pero la placa madre '{motherboard.nombre}' requiere '{mb_spec.socket}'."
                )
            else:
                compatibilidad_mensajes.append(
                    f"✅ Sockets compatibles ({cpu_spec.socket or mb_spec.socket})."
                )
        else:
            compatibilidad_mensajes.append(
                f"⚠️ Falta especificación de socket para verificar compatibilidad entre '{cpu.nombre}' y '{motherboard.nombre}'."
            )
            
    # 2. Verificar Placa Madre y Memoria RAM (Tipo de RAM)
    if motherboard and ram:
        mb_spec = specs.get(motherboard.id_producto)
        ram_spec = specs.get(ram.id_producto)
        
        if mb_spec and ram_spec:
            if mb_spec.tipo_ram and ram_spec.tipo_ram and mb_spec.tipo_ram.strip().lower() != ram_spec.tipo_ram.strip().lower():
                es_compatible = False
                compatibilidad_mensajes.append(
                    f"❌ Incompatibilidad de RAM: La placa madre '{motherboard.nombre}' soporta memoria '{mb_spec.tipo_ram}' pero has seleccionado memoria RAM tipo '{ram_spec.tipo_ram}' ('{ram.nombre}')."
                )
            else:
                compatibilidad_mensajes.append(
                    f"✅ Memorias RAM compatibles ({mb_spec.tipo_ram or ram_spec.tipo_ram})."
                )
        else:
            compatibilidad_mensajes.append(
                f"⚠️ Falta especificación de tipo de RAM para verificar compatibilidad entre la placa madre y la memoria."
            )
 
    # 3. Verificar Fuente de Poder y Consumo Estimado
    watts_cpu = 0
    watts_gpu = 0
    
    if cpu:
        cpu_spec = specs.get(cpu.id_producto)
        if cpu_spec and cpu_spec.watts:
            try:
                watts_cpu = int(''.join(filter(str.isdigit, cpu_spec.watts)))
            except ValueError:
                watts_cpu = 125  # Valor por defecto típico para CPU alto rendimiento
        else:
            watts_cpu = 125
            
    if gpu:
        gpu_spec = specs.get(gpu.id_producto)
        if gpu_spec and gpu_spec.watts:
            try:
                watts_gpu = int(''.join(filter(str.isdigit, gpu_spec.watts)))
            except ValueError:
                watts_gpu = 250  # Valor por defecto típico para GPU dedicada
        else:
            watts_gpu = 200
 
    # Margen adicional para placa madre, almacenamiento, ventiladores, etc.
    overhead = 150
    watts_totales_estimados = watts_cpu + watts_gpu + overhead
    
    if psu:
        psu_spec = specs.get(psu.id_producto)
        watts_psu = 0
        if psu_spec and psu_spec.watts:
            try:
                watts_psu = int(''.join(filter(str.isdigit, psu_spec.watts)))
            except ValueError:
                pass
        
        # Si no se pudo parsear o no tiene el campo, intentar parsear del nombre
        if watts_psu == 0:
            import re
            match = re.search(r'(\d+)W', psu.nombre, re.IGNORECASE)
            if match:
                watts_psu = int(match.group(1))
            else:
                watts_psu = 600 # Valor por defecto seguro si no se especifica
                
        if watts_psu < watts_totales_estimados:
            es_compatible = False
            compatibilidad_mensajes.append(
                f"❌ Energía Insuficiente: El consumo estimado del sistema es de {watts_totales_estimados}W (CPU: {watts_cpu}W + GPU: {watts_gpu}W + base: {overhead}W), pero la fuente de poder '{psu.nombre}' solo provee {watts_psu}W."
            )
        else:
            compatibilidad_mensajes.append(
                f"✅ Fuente de poder suficiente: {watts_psu}W provistos vs {watts_totales_estimados}W estimados."
            )
    else:
        if cpu or gpu:
            compatibilidad_mensajes.append(
                f"ℹ️ Consumo estimado del sistema actual: {watts_totales_estimados}W. Se recomienda seleccionar una fuente de poder de al menos {watts_totales_estimados + 100}W."
            )
 
    return {
        "compatible": es_compatible,
        "mensajes": compatibilidad_mensajes,
        "consumo_estimado_w": watts_totales_estimados,
        "precio_total_bs": float(precio_total_bs),
        "precio_total_usd": float(precio_total_usd)
    }

def recomendar_componentes_compatibles(productos_seleccionados_ids, categoria_objetivo):
    """
    Recomienda productos de una categoría específica que sean compatibles
    con los productos ya seleccionados.
    """
    productos_sel, specs_sel = obtener_especificaciones_productos(productos_seleccionados_ids)
    
    cpu_sel = None
    motherboard_sel = None
    
    for prod in productos_sel:
        cat = prod.categoria.nombre.lower()
        if "procesador" in cat or "cpu" in cat:
            cpu_sel = prod
        elif "placa" in cat or "motherboard" in cat:
            motherboard_sel = prod
 
    # Buscar todos los productos activos de la categoría objetivo pre-cargando la marca
    candidatos = Producto.objects.filter(
        categoria__nombre__icontains=categoria_objetivo,
        estado=True,
        stock__gt=0
    ).select_related('marca')
    
    candidatos_specs = {spec.producto_id: spec for spec in ProductoEspecificacion.objects.filter(producto__in=candidatos, estado=True)}
    recomendados = []
 
    for cand in candidatos:
        cand_spec = candidatos_specs.get(cand.id_producto)
        es_compatible = True
        razon_incompatibilidad = ""
        
        # Reglas cruzadas:
        # A. Si se busca Placa Madre, debe ser compatible con la CPU seleccionada (Socket)
        if "placa" in categoria_objetivo.lower() or "motherboard" in categoria_objetivo.lower():
            if cpu_sel:
                cpu_spec = specs_sel.get(cpu_sel.id_producto)
                if cpu_spec and cand_spec:
                    if cpu_spec.socket and cand_spec.socket and cpu_spec.socket.strip().lower() != cand_spec.socket.strip().lower():
                        es_compatible = False
                        razon_incompatibilidad = f"Socket diferente ({cand_spec.socket} vs {cpu_spec.socket})"
                        
        # B. Si se busca CPU, debe ser compatible con la Placa Madre seleccionada (Socket)
        elif "procesador" in categoria_objetivo.lower() or "cpu" in categoria_objetivo.lower():
            if motherboard_sel:
                mb_spec = specs_sel.get(motherboard_sel.id_producto)
                if mb_spec and cand_spec:
                    if mb_spec.socket and cand_spec.socket and mb_spec.socket.strip().lower() != cand_spec.socket.strip().lower():
                        es_compatible = False
                        razon_incompatibilidad = f"Socket diferente ({cand_spec.socket} vs {mb_spec.socket})"
                        
        # C. Si se busca Memoria RAM, debe ser compatible con la Placa Madre seleccionada (DDR4 vs DDR5)
        elif "ram" in categoria_objetivo.lower():
            if motherboard_sel:
                mb_spec = specs_sel.get(motherboard_sel.id_producto)
                if mb_spec and cand_spec:
                    if mb_spec.tipo_ram and cand_spec.tipo_ram and mb_spec.tipo_ram.strip().lower() != cand_spec.tipo_ram.strip().lower():
                        es_compatible = False
                        razon_incompatibilidad = f"Tipo de RAM incompatible ({cand_spec.tipo_ram} vs requiere {mb_spec.tipo_ram})"
 
        if es_compatible:
            recomendados.append({
                "id_producto": str(cand.id_producto),
                "nombre": cand.nombre,
                "precio_actual": float(cand.precio_actual),
                "precio_usd": float(cand.precio_usd),
                "stock": cand.stock,
                "marca": cand.marca.nombre,
                "socket": cand_spec.socket if cand_spec else None,
                "tipo_ram": cand_spec.tipo_ram if cand_spec else None,
            })
            
    return recomendados[:10]  # Limitar a las 10 mejores opciones compatibles
