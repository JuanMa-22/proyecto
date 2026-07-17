from django.shortcuts import render, redirect
from .models import Venta
from apps.cliente.models import Cliente
from apps.usuario.models import Usuario
from apps.detalleVenta.models import DetalleVenta
from apps.producto.models import Producto
from apps.movimiento.models import Movimiento
from django.utils import timezone
from apps.tipoMovimiento.models import tipoMovimiento
from apps.usuario.decorators import login_requerido, solo_admin, es_vendedor
from apps.web.reportes_generator import generar_pdf_reporte, generar_excel_reporte, generar_pdf_recibo
from datetime import date
from decimal import Decimal
from django.contrib import messages
from apps.tipoCambio.models import TipoCambio
from apps.lote.servicios import consumir_lotes_peps
from django.db import transaction


@login_requerido
def index(request):
    ventas = Venta.objects.select_related('cliente', 'usuario').prefetch_related('detalleventa_set__producto__categoria')
    if es_vendedor(request):
        ventas = ventas.filter(usuario_id=request.session.get('usuario_id'))
    clientes = Cliente.objects.all()
    productos = Producto.objects.select_related('categoria').filter(estado=True, stock__gt=0).order_by('categoria__nombre', 'nombre')
    return render(request, 'venta/index.html', {
        'ventas': ventas,
        'clientes': clientes,
        'productos': productos
    })

@login_requerido
def crearVenta(request):
    clientes = Cliente.objects.all()
    usuarios = Usuario.objects.all()

    if request.method == 'POST':
        try:
            with transaction.atomic():
                cliente_id = request.POST.get('cliente')
                if not cliente_id:
                    raise ValueError("El cliente es requerido.")
                cliente = Cliente.objects.get(id_cliente=cliente_id)

                usuario_id = request.session.get('usuario_id')
                if not usuario_id:
                    raise ValueError("Sesión inválida o expirada.")
                usuario = Usuario.objects.get(id_usuario=usuario_id)

                tipo_cambio = TipoCambio.objects.filter(estado=True).order_by('-fecha', '-created_at').first()
                tipo_cambio_val = tipo_cambio.valor if tipo_cambio else Decimal('6.96')

                producto_ids = request.POST.getlist('producto[]')
                cantidades = request.POST.getlist('cantidad[]')
                precios = request.POST.getlist('precio[]')
                descuentos = request.POST.getlist('descuento[]')

                if not producto_ids or len(producto_ids) == 0:
                    raise ValueError("Debe agregar al menos un producto a la venta.")

                calculated_total = Decimal('0.00')
                detalles_procesar = []

                for i in range(len(producto_ids)):
                    prod_id = producto_ids[i]
                    if not prod_id:
                        continue
                    # Bloqueo de fila para evitar condiciones de carrera en stock
                    prod = Producto.objects.select_for_update().get(id_producto=prod_id)
                    cant = int(cantidades[i])
                    
                    if cant <= 0:
                        raise ValueError(f"La cantidad para el producto '{prod.nombre}' debe ser mayor a 0.")
                    if prod.stock < cant:
                        raise ValueError(f"Stock insuficiente para '{prod.nombre}'. Disponible: {prod.stock}, Solicitado: {cant}")

                    price_db = prod.precio_actual
                    if price_db < 0:
                        raise ValueError("El precio no puede ser negativo.")

                    desc_val = Decimal(descuentos[i]) if i < len(descuentos) and descuentos[i] else Decimal('0.00')
                    if desc_val < 0:
                        raise ValueError("El descuento no puede ser negativo.")
                    if desc_val > price_db:
                        raise ValueError(f"El descuento ({desc_val}) no puede superar el precio del producto ({price_db}).")

                    subtotal_item = (price_db - desc_val) * cant
                    calculated_total += subtotal_item

                    detalles_procesar.append({
                        'producto': prod,
                        'cantidad': cant,
                        'precio': price_db,
                        'descuento': desc_val
                    })

                venta = Venta.objects.create(
                    cliente=cliente,
                    usuario=usuario,
                    fecha=request.POST['fecha'],
                    total=calculated_total,
                    tipo_cambio_valor=tipo_cambio_val,
                    estado=True
                )

                for item in detalles_procesar:
                    agregar_detalle_venta(
                        venta, 
                        item['producto'], 
                        item['cantidad'], 
                        item['precio'], 
                        float(item['descuento'])
                    )

            messages.success(request, "Venta registrada exitosamente.")
            return redirect('venta:index')

        except Exception as ex:
            messages.error(request, f'Error al registrar venta: {str(ex)}')
            return redirect('venta:index')

    productos = Producto.objects.select_related('categoria').filter(estado=True, stock__gt=0).order_by('categoria__nombre', 'nombre')

    return render(request, 'venta/crear.html', {
        'clientes': clientes,
        'usuarios': usuarios,
        'productos': productos
    })

def agregar_detalle_venta(venta, producto, cantidad, precio, descuento=0.0):
    """
    Registra un ítem de venta aplicando metodología PEPS/FIFO para descontar
    stock: consume primero el lote más antiguo disponible y registra la trazabilidad.
    """
    # Validación previa usando stock del producto (respaldo rápido)
    if producto.stock < cantidad:
        raise ValueError("Stock insuficiente")

    stock_anterior = producto.stock

    detalle = DetalleVenta.objects.create(
        venta=venta,
        producto=producto,
        cantidad=cantidad,
        precio_unitario=precio,
        descuento=descuento,
        subtotal=(cantidad * precio) - descuento,
        estado=True
    )

    # ── PEPS/FIFO: descontar del lote más antiguo disponible ─────────────────
    consumir_lotes_peps(
        producto=producto,
        detalle_venta=detalle,
        cantidad=cantidad,
    )
    # Nota: consumir_lotes_peps actualiza producto.stock internamente y
    # registra LoteConsumo para trazabilidad completa.
    # Refrescamos la instancia para obtener el stock actualizado.
    producto.refresh_from_db(fields=['stock'])
    # ─────────────────────────────────────────────────────────────────────────

    tipo_salida = tipoMovimiento.objects.filter(nombre="SALIDA").first()
    if not tipo_salida:
        tipo_salida = tipoMovimiento.objects.filter(nombre__icontains="SALIDA").first()
    if not tipo_salida:
        tipo_salida = tipoMovimiento.objects.create(nombre="SALIDA", estado=True)

    Movimiento.objects.create(
        producto=producto,
        detalleVenta=detalle,
        tipoMovimiento=tipo_salida,
        cantidad=cantidad,
        stock_anterior=stock_anterior,
        stock_actual=producto.stock,
        motivo=f"Venta #{venta.id_venta}",
    )

    return detalle

@login_requerido
def recibo_venta(request, id_venta):
    """Genera el recibo de venta como PDF usando ReportLab."""
    try:
        if es_vendedor(request):
            venta = Venta.objects.select_related('cliente', 'usuario').get(id_venta=id_venta, usuario_id=request.session.get('usuario_id'))
        else:
            venta = Venta.objects.select_related('cliente', 'usuario').get(id_venta=id_venta)
    except Venta.DoesNotExist:
        if es_vendedor(request):
            return render(request, 'layout/acceso_denegado.html', status=403)
        raise
    detalles = DetalleVenta.objects.select_related('producto').filter(venta=venta)
    return generar_pdf_recibo(venta, detalles)


# ─── Reportes de Ventas ───────────────────────────────────────────────────────

MESES = [
    (1, 'Enero'), (2, 'Febrero'), (3, 'Marzo'), (4, 'Abril'),
    (5, 'Mayo'), (6, 'Junio'), (7, 'Julio'), (8, 'Agosto'),
    (9, 'Septiembre'), (10, 'Octubre'), (11, 'Noviembre'), (12, 'Diciembre'),
]

@login_requerido
def reporte_venta_view(request):
    """Renderiza la interfaz de reportes de ventas con filtros."""
    tipo_filtro = request.GET.get('tipo_filtro', '')
    ventas = None
    total_sum = 0

    if tipo_filtro:
        ventas = Venta.objects.select_related('cliente', 'usuario').filter(estado=True)
        if es_vendedor(request):
            ventas = ventas.filter(usuario_id=request.session.get('usuario_id'))
            
        if tipo_filtro == 'rango':
            fecha_desde = request.GET.get('fecha_desde')
            fecha_hasta = request.GET.get('fecha_hasta')
            if fecha_desde and fecha_hasta:
                ventas = ventas.filter(fecha__gte=fecha_desde, fecha__lte=fecha_hasta)

        elif tipo_filtro == 'mes':
            mes = request.GET.get('mes')
            anio = request.GET.get('anio_mes')
            if mes and anio:
                ventas = ventas.filter(fecha__month=int(mes), fecha__year=int(anio))

        elif tipo_filtro == 'anio':
            anio = request.GET.get('anio')
            if anio:
                ventas = ventas.filter(fecha__year=int(anio))

        ventas = ventas.order_by('-fecha')
        total_sum = sum(v.total for v in ventas)

    ventas_anios = Venta.objects.filter(estado=True)
    if es_vendedor(request):
        ventas_anios = ventas_anios.filter(usuario_id=request.session.get('usuario_id'))
        
    anios_disponibles = list(
        ventas_anios.dates('fecha', 'year', order='DESC')
        .values_list('fecha__year', flat=True).distinct()
    )
    if not anios_disponibles:
        anios_disponibles = [timezone.now().year]

    return render(request, 'venta/reportes.html', {
        'ventas': ventas,
        'total_sum': total_sum,
        'tipo_filtro': tipo_filtro,
        'anios_disponibles': anios_disponibles,
        'meses': MESES,
        'request': request,
    })


def _filtrar_ventas(request):
    """Función auxiliar que aplica los mismos filtros de fecha a las ventas."""
    tipo_filtro = request.GET.get('tipo_filtro', '')
    ventas = Venta.objects.select_related('cliente', 'usuario').filter(estado=True)
    if es_vendedor(request):
        ventas = ventas.filter(usuario_id=request.session.get('usuario_id'))

    if tipo_filtro == 'rango':
        fecha_desde = request.GET.get('fecha_desde')
        fecha_hasta = request.GET.get('fecha_hasta')
        if fecha_desde and fecha_hasta:
            ventas = ventas.filter(fecha__gte=fecha_desde, fecha__lte=fecha_hasta)

    elif tipo_filtro == 'mes':
        mes = request.GET.get('mes')
        anio = request.GET.get('anio_mes')
        if mes and anio:
            ventas = ventas.filter(fecha__month=int(mes), fecha__year=int(anio))

    elif tipo_filtro == 'anio':
        anio = request.GET.get('anio')
        if anio:
            ventas = ventas.filter(fecha__year=int(anio))

    return ventas.order_by('-fecha')


@login_requerido
def reporte_venta_pdf(request):
    ventas = _filtrar_ventas(request)
    headers = ['N° Venta (parcial)', 'Cliente', 'Atendido por', 'Fecha', 'Total (Bs)']
    data = []
    total_general = 0
    for v in ventas:
        data.append([
            str(v.id_venta)[:18] + '...',
            f"{v.cliente.nombre} {v.cliente.apellido}",
            f"{v.usuario.nombre} {v.usuario.apellido}",
            v.fecha.strftime('%d/%m/%Y'),
            f"Bs. {float(v.total):.2f}",
        ])
        total_general += float(v.total)
    # Fila de totales
    data.append(['', '', '', 'TOTAL GENERAL:', f"Bs. {total_general:.2f}"])
    return generar_pdf_reporte('Reporte de Ventas', headers, data, 'reporte_ventas.pdf')


@login_requerido
def reporte_venta_excel(request):
    ventas = _filtrar_ventas(request)
    headers = ['N° Venta', 'Cliente', 'Atendido por', 'Fecha', 'Total (Bs)']
    data = []
    total_general = 0
    for v in ventas:
        data.append([
            str(v.id_venta),
            f"{v.cliente.nombre} {v.cliente.apellido}",
            f"{v.usuario.nombre} {v.usuario.apellido}",
            v.fecha.strftime('%d/%m/%Y'),
            float(v.total),
        ])
        total_general += float(v.total)
    data.append(['', '', '', 'TOTAL GENERAL', total_general])
    return generar_excel_reporte('Reporte de Ventas', headers, data, 'reporte_ventas.xlsx')