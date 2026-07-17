from django.shortcuts import render, redirect
from django.db.models import Sum, Count
from django.contrib import messages
from apps.venta.models import Venta
from apps.compra.models import Compra
from apps.producto.models import Producto
from apps.cliente.models import Cliente
from apps.detalleVenta.models import DetalleVenta
from apps.categoria.models import Categoria
from django.utils import timezone   
from datetime import timedelta
import json
from apps.usuario.decorators import login_requerido, es_admin
from decimal import Decimal
from apps.lote.models import LoteProducto
from apps.tipoCambio.models import TipoCambio

@login_requerido
def dashboard(request):
    hoy = timezone.localdate()

    # Ventas activas
    ventas = Venta.objects.filter(estado=True)
    is_administrator = es_admin(request)
    
    if not is_administrator:
        ventas = ventas.filter(usuario_id=request.session.get('usuario_id'))
    total_ventas = ventas.aggregate(Sum('total'))['total__sum'] or Decimal('0.00')
    total_ventas_count = ventas.count()

    if is_administrator:
        # Compras activas
        compras = Compra.objects.filter(estado=True)
        total_compras_bs = Decimal('0.00')
        for c in compras:
            total_compras_bs += c.total * c.tipo_cambio_valor

        # --- CÁLCULO DE GANANCIAS (LÓGICA PEPS / FIFO) ---
        tipo_cambio_actual = TipoCambio.objects.filter(estado=True).order_by('-fecha', '-created_at').first()
        tc_actual = tipo_cambio_actual.valor if tipo_cambio_actual else Decimal('6.96')

        cogs_historico = Decimal('0.00')
        cogs_reposicion = Decimal('0.00')

        # Prefetch consumos de lotes y compras para optimizar
        ventas_cogs = Venta.objects.filter(estado=True).prefetch_related(
            'detalleventa_set__consumos_lote__lote__detalle_compra__compra'
        )
        for v in ventas_cogs:
            for d in v.detalleventa_set.all():
                for c in d.consumos_lote.all():
                    costo_usd = c.lote.precio_costo_usd
                    compra_ref = c.lote.detalle_compra.compra if (c.lote.detalle_compra and c.lote.detalle_compra.compra) else None
                    tc_compra = compra_ref.tipo_cambio_valor if (compra_ref and hasattr(compra_ref, 'tipo_cambio_valor')) else Decimal('6.96')

                    cogs_historico += Decimal(str(c.cantidad)) * costo_usd * tc_compra
                    cogs_reposicion += Decimal(str(c.cantidad)) * costo_usd * tc_actual

        ganancias_contables = total_ventas - cogs_historico
        ganancias_reposicion = total_ventas - cogs_reposicion
        margen_promedio = (ganancias_contables / total_ventas * 100) if total_ventas > Decimal('0.00') else Decimal('0.00')

        # --- INVERSIÓN EN INVENTARIO ACTIVO ---
        lotes_activos = LoteProducto.objects.filter(cantidad_disponible__gt=0, estado=True).select_related('detalle_compra__compra')
        inventario_usd = Decimal('0.00')
        inventario_bs = Decimal('0.00')
        for lote in lotes_activos:
            compra_ref = lote.detalle_compra.compra if (lote.detalle_compra and lote.detalle_compra.compra) else None
            tc_compra = compra_ref.tipo_cambio_valor if (compra_ref and hasattr(compra_ref, 'tipo_cambio_valor')) else Decimal('6.96')
            
            inventario_usd += Decimal(str(lote.cantidad_disponible)) * lote.precio_costo_usd
            inventario_bs += Decimal(str(lote.cantidad_disponible)) * lote.precio_costo_usd * tc_compra
    else:
        # Vendedores no tienen acceso a compras, ganancias ni inventarios
        total_compras_bs = Decimal('0.00')
        ganancias_contables = Decimal('0.00')
        ganancias_reposicion = Decimal('0.00')
        margen_promedio = Decimal('0.00')
        inventario_usd = Decimal('0.00')
        inventario_bs = Decimal('0.00')

    # Counts
    total_productos = Producto.objects.filter(estado=True).count()
    total_clientes = Cliente.objects.filter(estado=True).count()

    # Ventas últimos 7 días para gráfico
    labels = []
    data_ventas = []
    for i in range(6, -1, -1):
        dia = hoy - timedelta(days=i)
        total_dia = ventas.filter(fecha=dia).aggregate(Sum('total'))['total__sum'] or Decimal('0.00')
        labels.append(dia.strftime('%d %b'))
        data_ventas.append(float(total_dia))

    # Top 5 productos más vendidos (por cantidad en detalles de venta)
    detalles = DetalleVenta.objects.all()
    if not is_administrator:
        detalles = detalles.filter(venta__usuario_id=request.session.get('usuario_id'))
    top_productos = (
        detalles
        .values('producto__nombre', 'producto__imagen')
        .annotate(total_vendido=Sum('cantidad'))
        .order_by('-total_vendido')[:5]
    )

    # Distribución por categoría (por número de productos activos)
    categorias_dist = (
        Producto.objects.filter(estado=True)
        .values('categoria__nombre')
        .annotate(total=Count('id_producto'))
        .order_by('-total')[:6]
    )
    cat_labels = [c['categoria__nombre'] or 'Sin categoría' for c in categorias_dist]
    cat_data = [c['total'] for c in categorias_dist]

    # Productos con bajo stock (menos de 10)
    productos_bajo_stock = Producto.objects.filter(estado=True, stock__lt=10).order_by('stock')[:5]

    context = {
        'total_ventas': float(total_ventas),
        'total_ventas_count': total_ventas_count,
        'total_compras': float(total_compras_bs),  # Ahora en Bs.
        'total_productos': total_productos,
        'total_clientes': total_clientes,
        'ganancias': float(ganancias_contables),
        'ganancias_reposicion': float(ganancias_reposicion),
        'margen_promedio': float(margen_promedio),
        'inventario_usd': float(inventario_usd),
        'inventario_bs': float(inventario_bs),
        'chart_labels': json.dumps(labels),
        'chart_data': json.dumps(data_ventas),
        'top_productos': top_productos,
        'cat_labels': json.dumps(cat_labels),
        'cat_data': json.dumps(cat_data),
        'productos_bajo_stock': productos_bajo_stock,
        'es_admin': is_administrator,
    }
    return render(request, 'web/dashboard.html', context)

# Vistas para la página web premium
def inicio_pagina(request):
    query = request.GET.get('q', '').strip()
    categoria_id = request.GET.get('categoria', '').strip()

    productos = Producto.objects.filter(estado=True, stock__gt=0).select_related('categoria', 'marca').prefetch_related('productoespecificacion_set')

    if query:
        productos = productos.filter(nombre__icontains=query)
    if categoria_id:
        productos = productos.filter(categoria__id_categoria=categoria_id)

    productos = productos.order_by('-created_at')

    # Todas las categorías activas para el sidebar que tengan productos en stock
    from django.db.models import Exists, OuterRef
    productos_activos_con_stock = Producto.objects.filter(
        categoria=OuterRef('pk'),
        estado=True,
        stock__gt=0
    )
    categorias = Categoria.objects.filter(estado=True).annotate(
        tiene_productos_con_stock=Exists(productos_activos_con_stock)
    ).filter(tiene_productos_con_stock=True)

    # Categoría activa para resaltarla en sidebar
    categoria_activa = None
    if categoria_id:
        try:
            categoria_activa = Categoria.objects.get(id_categoria=categoria_id)
        except Categoria.DoesNotExist:
            pass

    # Si no hay filtros, agrupamos los productos por categoría
    categorias_con_productos = []
    mostrar_agrupados = False
    
    if not query and not categoria_id:
        mostrar_agrupados = True
        for cat in categorias:
            cat_productos = Producto.objects.filter(categoria=cat, estado=True, stock__gt=0).select_related('marca').prefetch_related('productoespecificacion_set').order_by('-created_at')
            if cat_productos.exists():
                categorias_con_productos.append({
                    'categoria': cat,
                    'productos': cat_productos,
                    'count': cat_productos.count()
                })
        # Si no hay ningún producto en ninguna categoría, desactivamos la agrupación para mostrar el estado vacío
        if not categorias_con_productos:
            mostrar_agrupados = False

    return render(request, 'pagina/inicio.html', {
        'productos': productos,
        'categorias': categorias,
        'query': query,
        'categoria_seleccionada': categoria_id,
        'categoria_activa': categoria_activa,
        'mostrar_agrupados': mostrar_agrupados,
        'categorias_con_productos': categorias_con_productos,
    })

def nosotros_pagina(request):
    return render(request, 'pagina/nosotros.html')

def servicios_pagina(request):
    return render(request, 'pagina/servicios.html')

def ubicacion_pagina(request):
    return render(request, 'pagina/ubicacion.html')

def detalle_producto(request, slug):
    from django.shortcuts import get_object_or_404
    producto = get_object_or_404(
        Producto.objects.filter(estado=True)
        .select_related('categoria', 'marca')
        .prefetch_related('productoespecificacion_set'),
        slug=slug
    )
    productos_relacionados = Producto.objects.filter(
        categoria=producto.categoria, estado=True, stock__gt=0
    ).exclude(id_producto=producto.id_producto)[:4]
    
    return render(request, 'pagina/detalle_producto.html', {
        'producto': producto,
        'productos_relacionados': productos_relacionados,
    })

def categoria_pagina(request, slug):
    from django.shortcuts import get_object_or_404
    categoria = get_object_or_404(Categoria, slug=slug, estado=True)
    productos = Producto.objects.filter(categoria=categoria, estado=True, stock__gt=0).select_related('marca')
    from django.db.models import Exists, OuterRef
    productos_activos_con_stock = Producto.objects.filter(
        categoria=OuterRef('pk'),
        estado=True,
        stock__gt=0
    )
    categorias = Categoria.objects.filter(estado=True).annotate(
        tiene_productos_con_stock=Exists(productos_activos_con_stock)
    ).filter(tiene_productos_con_stock=True)
    
    return render(request, 'pagina/categoria_productos.html', {
        'categoria_activa': categoria,
        'productos': productos,
        'categorias': categorias,
    })

def robots_txt(request):
    from django.http import HttpResponse
    lines = [
        "User-agent: *",
        "Disallow: /admin/",
        "Disallow: /usuarios/",
        "Disallow: /ventas/",
        "Disallow: /compras/",
        "Disallow: /inventario/",
        "Disallow: /reportes/",
        "Disallow: /login/",
        "Disallow: /dashboard/",
        "",
        f"Sitemap: {request.scheme}://{request.get_host()}/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


