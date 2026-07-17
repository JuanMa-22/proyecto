from django.shortcuts import render, redirect
from .models import Compra
from apps.proveedor.models import Proveedor
from apps.usuario.models import Usuario
from decimal import Decimal
from apps.historialPrecio.models import HistorialPrecio
from apps.detalleCompra.models import DetalleCompra
from apps.producto.models import Producto
from apps.movimiento.models import Movimiento
from apps.tipoMovimiento.models import tipoMovimiento
from apps.tipoCambio.models import TipoCambio
from apps.categoria.models import Categoria
from apps.marca.models import Marca
from django.utils import timezone
from apps.usuario.decorators import solo_admin
from django.contrib import messages
from apps.lote.servicios import crear_lote_desde_compra
from django.db import transaction
from apps.web.reportes_generator import generar_pdf_reporte, generar_excel_reporte

@solo_admin
def index(request):
    compras = Compra.objects.select_related('proveedor', 'usuario').prefetch_related('detallecompra_set__producto')
    proveedores = Proveedor.objects.all()
    productos = Producto.objects.select_related('categoria').filter(estado=True).order_by('categoria__nombre', 'nombre')
    categorias = Categoria.objects.all()
    marcas = Marca.objects.all()
    tipo_cambio = TipoCambio.objects.filter(estado=True).order_by('-fecha', '-created_at').first()
    
    return render(request, 'compra/index.html', {
        'compras': compras,
        'proveedores': proveedores,
        'productos': productos,
        'categorias': categorias,
        'marcas': marcas,
        'tipo_cambio': tipo_cambio
    })

@solo_admin
def crearCompra(request):
    proveedores = Proveedor.objects.all()
    usuarios = Usuario.objects.all()

    if request.method == 'POST':
        try:
            with transaction.atomic():
                proveedor_id = request.POST.get('proveedor_id')
                if not proveedor_id:
                    raise ValueError("El proveedor es requerido.")
                proveedor = Proveedor.objects.get(id_proveedor=proveedor_id)

                usuario_id = request.session.get('usuario_id')
                if not usuario_id:
                    raise ValueError("Sesión inválida o expirada.")
                usuario = Usuario.objects.get(id_usuario=usuario_id)

                tipo_cambio = TipoCambio.objects.filter(estado=True).order_by('-fecha', '-created_at').first()
                tipo_cambio_val = tipo_cambio.valor if tipo_cambio else Decimal('6.96')

                producto_ids = request.POST.getlist('producto[]')
                cantidades = request.POST.getlist('cantidad[]')
                precios = request.POST.getlist('precio[]')
                precios_venta = request.POST.getlist('precio_venta[]')

                if not producto_ids or len(producto_ids) == 0:
                    raise ValueError("Debe agregar al menos un producto a la compra.")

                calculated_total = Decimal('0.00')
                detalles_procesar = []

                for i in range(len(producto_ids)):
                    prod_id = producto_ids[i]
                    if not prod_id:
                        continue
                    prod = Producto.objects.select_for_update().get(id_producto=prod_id)
                    cant = int(cantidades[i])
                    price = Decimal(precios[i])
                    price_v = Decimal(precios_venta[i]) if i < len(precios_venta) and precios_venta[i] else Decimal('0.00')

                    if cant <= 0:
                        raise ValueError(f"La cantidad para '{prod.nombre}' debe ser mayor a 0.")
                    if price < 0:
                        raise ValueError(f"El precio de compra para '{prod.nombre}' no puede ser negativo.")
                    if price_v < 0:
                        raise ValueError(f"El precio de venta para '{prod.nombre}' no puede ser negativo.")

                    calculated_total += price * cant
                    detalles_procesar.append({
                        'producto': prod,
                        'cantidad': cant,
                        'precio': price,
                        'precio_venta': price_v
                    })

                compra = Compra.objects.create(
                    proveedor=proveedor,
                    usuario=usuario,
                    fecha=request.POST['fecha'],
                    observacion=request.POST.get('observacion', ''),
                    total=calculated_total,
                    tipo_cambio_valor=tipo_cambio_val,
                    estado=True
                )

                for item in detalles_procesar:
                    agregar_detalle_compra(
                        compra,
                        item['producto'],
                        item['cantidad'],
                        float(item['precio']),
                        float(item['precio_venta'])
                    )

            messages.success(request, "Compra registrada exitosamente.")
            return redirect('compra:index')

        except Exception as ex:
            messages.error(request, f'Error al registrar compra: {str(ex)}')
            return redirect('compra:index')

    productos = Producto.objects.select_related('categoria').filter(estado=True).order_by('categoria__nombre', 'nombre')
    tipo_cambio = TipoCambio.objects.filter(estado=True).order_by('-fecha', '-created_at').first()

    return render(request, 'compra/crear.html', {
        'proveedores': proveedores,
        'usuarios': usuarios,
        'productos': productos,
        'tipo_cambio': tipo_cambio
    })

def agregar_detalle_compra(compra, producto, cantidad, precio, precio_venta):

    stock_anterior = producto.stock

    detalle = DetalleCompra.objects.create(
        compra=compra,
        producto=producto,
        cantidad=cantidad,
        precio_compra=precio,
        precio_venta=precio_venta,
        subtotal=cantidad * precio,
        estado=True
    )

    # ── PEPS/FIFO: crear lote para esta entrada de mercadería ────────────────
    crear_lote_desde_compra(
        compra=compra,
        detalle_compra=detalle,
        producto=producto,
        cantidad=cantidad,
        precio_usd=Decimal(str(precio)),
    )
    # ─────────────────────────────────────────────────────────────────────────

    # Actualizar precio del producto e historial de precios si el precio de compra o venta cambió
    pc_usd = Decimal(str(precio))
    pv_usd = Decimal(str(precio_venta))
    tipo_cambio = TipoCambio.objects.filter(estado=True).order_by('-fecha', '-created_at').first()
    tipo_cambio_val = tipo_cambio.valor if tipo_cambio else Decimal('6.96')

    # Desactivar historial activo actual
    HistorialPrecio.objects.filter(
        producto=producto,
        estado=True
    ).update(
        estado=False,
        fecha_fin=timezone.now()
    )

    # Crear nuevo registro en el historial de precios
    if tipo_cambio:
        HistorialPrecio.objects.create(
            producto=producto,
            tipo_cambio=tipo_cambio,
            precio_compra=pc_usd,
            precio_venta=pv_usd * tipo_cambio.valor,
            fecha_inicio=timezone.now()
        )

    # Actualizamos el producto con el nuevo precio de venta (en USD) y precio_actual (en Bs)
    producto.precio_usd = pv_usd
    producto.precio_actual = pv_usd * tipo_cambio_val
    producto.save(update_fields=['precio_usd', 'precio_actual'])

    # Refrescamos la instancia para obtener el stock actualizado de los lotes
    producto.refresh_from_db(fields=['stock'])

    tipo_entrada = tipoMovimiento.objects.filter(nombre="ENTRADA").first()
    if not tipo_entrada:
        tipo_entrada = tipoMovimiento.objects.filter(nombre__icontains="ENTRADA").first()
    if not tipo_entrada:
        tipo_entrada = tipoMovimiento.objects.create(nombre="ENTRADA", estado=True)

    Movimiento.objects.create(
        producto=producto,
        detalleCompra=detalle,
        tipoMovimiento=tipo_entrada,
        cantidad=cantidad,
        stock_anterior=stock_anterior,
        stock_actual=producto.stock,
        motivo=f"Compra #{compra.id_compra}",
    )

    return detalle


from django.utils import timezone

MESES = [
    (1, 'Enero'), (2, 'Febrero'), (3, 'Marzo'), (4, 'Abril'),
    (5, 'Mayo'), (6, 'Junio'), (7, 'Julio'), (8, 'Agosto'),
    (9, 'Septiembre'), (10, 'Octubre'), (11, 'Noviembre'), (12, 'Diciembre'),
]


# ─── Reportes de Compras ──────────────────────────────────────────────────────

@solo_admin
def reporte_compra_view(request):
    """Renderiza la interfaz de reportes de compras con filtros."""
    tipo_filtro = request.GET.get('tipo_filtro', '')
    compras = None
    total_sum = 0

    if tipo_filtro:
        compras = Compra.objects.select_related('proveedor', 'usuario').filter(estado=True)

        if tipo_filtro == 'rango':
            fecha_desde = request.GET.get('fecha_desde')
            fecha_hasta = request.GET.get('fecha_hasta')
            if fecha_desde and fecha_hasta:
                compras = compras.filter(fecha__gte=fecha_desde, fecha__lte=fecha_hasta)

        elif tipo_filtro == 'mes':
            mes = request.GET.get('mes')
            anio = request.GET.get('anio_mes')
            if mes and anio:
                compras = compras.filter(fecha__month=int(mes), fecha__year=int(anio))

        elif tipo_filtro == 'anio':
            anio = request.GET.get('anio')
            if anio:
                compras = compras.filter(fecha__year=int(anio))

        compras = compras.order_by('-fecha')
        total_sum = sum(c.total for c in compras)

    anios_disponibles = list(
        Compra.objects.dates('fecha', 'year', order='DESC')
        .values_list('fecha__year', flat=True).distinct()
    )
    if not anios_disponibles:
        anios_disponibles = [timezone.now().year]

    return render(request, 'compra/reportes.html', {
        'compras': compras,
        'total_sum': total_sum,
        'tipo_filtro': tipo_filtro,
        'anios_disponibles': anios_disponibles,
        'meses': MESES,
        'request': request,
    })


def _filtrar_compras(request):
    """Función auxiliar que aplica los filtros de fecha a las compras."""
    tipo_filtro = request.GET.get('tipo_filtro', '')
    compras = Compra.objects.select_related('proveedor', 'usuario').filter(estado=True)

    if tipo_filtro == 'rango':
        fecha_desde = request.GET.get('fecha_desde')
        fecha_hasta = request.GET.get('fecha_hasta')
        if fecha_desde and fecha_hasta:
            compras = compras.filter(fecha__gte=fecha_desde, fecha__lte=fecha_hasta)

    elif tipo_filtro == 'mes':
        mes = request.GET.get('mes')
        anio = request.GET.get('anio_mes')
        if mes and anio:
            compras = compras.filter(fecha__month=int(mes), fecha__year=int(anio))

    elif tipo_filtro == 'anio':
        anio = request.GET.get('anio')
        if anio:
            compras = compras.filter(fecha__year=int(anio))

    return compras.order_by('-fecha')


@solo_admin
def reporte_compra_pdf(request):
    compras = _filtrar_compras(request)
    headers = ['N° Compra (parcial)', 'Proveedor', 'Comprador', 'Fecha', 'Observación', 'Total (Bs)']
    data = []
    total_general = 0
    for c in compras:
        data.append([
            str(c.id_compra)[:18] + '...',
            c.proveedor.nombre,
            f"{c.usuario.nombre} {c.usuario.apellido}",
            c.fecha.strftime('%d/%m/%Y'),
            c.observacion or '-',
            f"Bs. {float(c.total):.2f}",
        ])
        total_general += float(c.total)
    data.append(['', '', '', '', 'TOTAL GENERAL:', f"Bs. {total_general:.2f}"])
    return generar_pdf_reporte('Reporte de Compras', headers, data, 'reporte_compras.pdf')


@solo_admin
def reporte_compra_excel(request):
    compras = _filtrar_compras(request)
    headers = ['N° Compra', 'Proveedor', 'Comprador', 'Fecha', 'Observación', 'Total (Bs)']
    data = []
    total_general = 0
    for c in compras:
        data.append([
            str(c.id_compra),
            c.proveedor.nombre,
            f"{c.usuario.nombre} {c.usuario.apellido}",
            c.fecha.strftime('%d/%m/%Y'),
            c.observacion or '-',
            float(c.total),
        ])
        total_general += float(c.total)
    data.append(['', '', '', '', 'TOTAL GENERAL', total_general])
    return generar_excel_reporte('Reporte de Compras', headers, data, 'reporte_compras.xlsx')
