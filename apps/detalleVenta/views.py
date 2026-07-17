from django.shortcuts import render, redirect
from apps.detalleVenta.models import DetalleVenta
from apps.venta.models import Venta
from apps.producto.models import Producto
from apps.movimiento.models import Movimiento
from django.utils import timezone

def index(request):
    detalleVentas = DetalleVenta.objects.all()
    return render(request, 'detalleVenta/index.html', {'detalleVentas': detalleVentas})

def crearDetalleVenta(request):
    ventas = Venta.objects.all()
    productos = Producto.objects.all()

    if request.method == 'POST':

        venta = Venta.objects.get(id_venta=request.POST['venta'])
        producto = Producto.objects.get(id_producto=request.POST['producto'])

        cantidad = int(request.POST['cantidad'])
        precio_unitario = float(request.POST['precio_unitario'])

        if producto.stock < cantidad:
            return render(request, 'detalleVenta/crear.html', {
                'error': 'Stock insuficiente',
                'ventas': ventas,
                'productos': productos
            })

        subtotal = cantidad * precio_unitario
        stock_anterior = producto.stock

        # 1. crear detalle
        detalle = DetalleVenta.objects.create(
            venta=venta,
            producto=producto,
            cantidad=cantidad,
            precio_unitario=precio_unitario,
            subtotal=subtotal,
            estado=True
        )

        producto.stock -= cantidad
        producto.save()

        from apps.tipoMovimiento.models import tipoMovimiento
        tipo_salida = tipoMovimiento.objects.filter(nombre="SALIDA").first()
        if not tipo_salida:
            tipo_salida = tipoMovimiento.objects.filter(nombre__icontains="SALIDA").first()
        if not tipo_salida:
            tipo_salida = tipoMovimiento.objects.create(nombre="SALIDA", estado=True)

        Movimiento.objects.create(
            producto=producto,
            tipoMovimiento=tipo_salida,
            cantidad=cantidad,
            stock_anterior=stock_anterior,
            stock_actual=producto.stock,
            motivo=f'Venta #{venta.id_venta}',
            fecha=timezone.now()
        )

        return redirect('detalleVenta:index')

    return render(request, 'detalleVenta/crear.html', {
        'ventas': ventas,
        'productos': productos
    })

