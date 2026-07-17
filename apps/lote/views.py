from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from .models import LoteProducto, LoteConsumo
from .servicios import inicializar_lotes_existentes
from apps.producto.models import Producto
from apps.categoria.models import Categoria
from apps.proveedor.models import Proveedor
from apps.usuario.decorators import login_requerido, solo_admin


@solo_admin
def index(request):
    """
    Vista principal de Gestión de Lotes (PEPS/FIFO).
    Muestra todos los lotes con filtros por producto, categoría, proveedor y estado.
    """
    lotes = LoteProducto.objects.select_related(
        'producto', 'producto__categoria', 'producto__marca', 'proveedor', 'detalle_compra'
    ).prefetch_related('consumos__detalle_venta__venta__cliente')

    # ── Filtros ──────────────────────────────────────────────────────────────
    filtro_producto  = request.GET.get('producto', '')
    filtro_categoria = request.GET.get('categoria', '')
    filtro_proveedor = request.GET.get('proveedor', '')
    filtro_estado    = request.GET.get('estado', '')

    if filtro_producto:
        lotes = lotes.filter(producto__id_producto=filtro_producto)

    if filtro_categoria:
        lotes = lotes.filter(producto__categoria__id_categoria=filtro_categoria)

    if filtro_proveedor:
        lotes = lotes.filter(proveedor__id_proveedor=filtro_proveedor)

    if filtro_estado == 'activo':
        lotes = lotes.filter(estado=True, cantidad_disponible__gt=0)
    elif filtro_estado == 'agotado':
        lotes = lotes.filter(cantidad_disponible=0)

    lotes = lotes.order_by('fecha_entrada', 'created_at')

    # ── Calcular antigüedad en días para cada lote ────────────────────────────
    hoy = timezone.localdate()
    lotes_con_antiguedad = []
    for lote in lotes:
        delta = hoy - lote.fecha_entrada
        dias  = delta.days
        anios = dias // 365
        meses = (dias % 365) // 30
        dias_r = (dias % 365) % 30

        if anios > 0:
            antiguedad_str = f"{anios} año{'s' if anios > 1 else ''}"
            if meses > 0:
                antiguedad_str += f" {meses} mes{'es' if meses > 1 else ''}"
        elif meses > 0:
            antiguedad_str = f"{meses} mes{'es' if meses > 1 else ''}"
        else:
            antiguedad_str = f"{dias_r} día{'s' if dias_r != 1 else ''}"

        lotes_con_antiguedad.append({
            'lote': lote,
            'antiguedad': antiguedad_str,
            'dias_totales': dias,
        })

    # ── Contexto ──────────────────────────────────────────────────────────────
    productos   = Producto.objects.filter(estado=True).order_by('nombre')
    categorias  = Categoria.objects.all().order_by('nombre')
    proveedores = Proveedor.objects.all().order_by('nombre')

    total_lotes     = len(lotes_con_antiguedad)
    lotes_activos   = sum(1 for l in lotes_con_antiguedad if l['lote'].cantidad_disponible > 0)
    lotes_agotados  = total_lotes - lotes_activos
    total_unidades  = sum(l['lote'].cantidad_disponible for l in lotes_con_antiguedad)

    return render(request, 'lote/index.html', {
        'lotes_con_antiguedad': lotes_con_antiguedad,
        'productos':   productos,
        'categorias':  categorias,
        'proveedores': proveedores,
        'filtro_producto':  filtro_producto,
        'filtro_categoria': filtro_categoria,
        'filtro_proveedor': filtro_proveedor,
        'filtro_estado':    filtro_estado,
        'total_lotes':    total_lotes,
        'lotes_activos':  lotes_activos,
        'lotes_agotados': lotes_agotados,
        'total_unidades': total_unidades,
    })


@solo_admin
def inicializar_lotes_view(request):
    """
    Vista de acción: inicializa o actualiza los lotes PEPS para productos existentes.
    Actualiza lotes sin proveedor usando el último DetalleCompra de cada producto.
    """
    if request.method == 'POST':
        creados, actualizados = inicializar_lotes_existentes()
        if creados > 0 or actualizados > 0:
            partes = []
            if creados > 0:
                partes.append(f'{creados} lote(s) creado(s)')
            if actualizados > 0:
                partes.append(f'{actualizados} lote(s) actualizados con proveedor')
            messages.success(request, f'✅ {" y ".join(partes)} exitosamente.')
        else:
            messages.info(request, 'ℹ️ Todos los lotes ya tienen proveedor asignado.')
        return redirect('lote:index')
    return redirect('lote:index')


@solo_admin
def detalle_lote(request, id_lote):
    """Vista de detalle de un lote: muestra el historial completo de consumos."""
    try:
        lote = LoteProducto.objects.select_related(
            'producto', 'proveedor', 'detalle_compra__compra'
        ).get(id_lote=id_lote)
    except LoteProducto.DoesNotExist:
        messages.error(request, 'Lote no encontrado.')
        return redirect('lote:index')

    consumos = LoteConsumo.objects.select_related(
        'detalle_venta__venta__cliente'
    ).filter(lote=lote).order_by('-fecha_consumo')

    hoy = timezone.localdate()
    delta = hoy - lote.fecha_entrada
    dias = delta.days
    anios = dias // 365
    meses = (dias % 365) // 30

    if anios > 0:
        antiguedad_str = f"{anios} año{'s' if anios > 1 else ''}"
        if meses > 0:
            antiguedad_str += f" {meses} mes{'es' if meses > 1 else ''}"
    elif meses > 0:
        antiguedad_str = f"{meses} mes{'es' if meses > 1 else ''}"
    else:
        antiguedad_str = f"{dias} día{'s' if dias != 1 else ''}"

    return render(request, 'lote/detalle.html', {
        'lote':        lote,
        'consumos':    consumos,
        'antiguedad':  antiguedad_str,
        'dias_totales': dias,
    })
