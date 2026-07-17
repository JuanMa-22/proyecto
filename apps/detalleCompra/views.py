from django.shortcuts import render, redirect
from apps.detalleCompra.models import DetalleCompra
from apps.compra.models import Compra
from apps.producto.models import Producto
from apps.movimiento.models import Movimiento
from django.utils import timezone

# Create your views here.
def crearDetalleCompra(request):
    compras = Compra.objects.all()
    productos = Producto.objects.all()

    if request.method == 'POST':

        compra = Compra.objects.get(id_compra=request.POST['compra_id'])
        producto = Producto.objects.get(id_producto=request.POST['producto_id'])

        cantidad = int(request.POST['cantidad'])
        precio_compra = float(request.POST['precio_compra'])

        subtotal = cantidad * precio_compra
        stock_anterior = producto.stock

        # 1. crear detalle
        detalle = DetalleCompra.objects.create(
            compra=compra,
            producto=producto,
            cantidad=cantidad,
            precio_compra=precio_compra,
            subtotal=subtotal,
            estado=True
        )

        # 2. actualizar stock (ENTRADA)
        producto.stock += cantidad
        producto.save()

        # 3. crear movimiento
        from apps.tipoMovimiento.models import tipoMovimiento
        tipo_entrada = tipoMovimiento.objects.filter(nombre="ENTRADA").first()
        if not tipo_entrada:
            tipo_entrada = tipoMovimiento.objects.filter(nombre__icontains="ENTRADA").first()
        if not tipo_entrada:
            tipo_entrada = tipoMovimiento.objects.create(nombre="ENTRADA", estado=True)

        Movimiento.objects.create(
            producto=producto,
            tipoMovimiento=tipo_entrada,
            cantidad=cantidad,
            stock_anterior=stock_anterior,
            stock_actual=producto.stock,
            motivo=f'Compra #{compra.id_compra}',
            fecha=timezone.now()
        )

        return redirect('detalleCompra:index')

    return render(request, 'detalleCompra/crear.html', {
        'compras': compras,
        'productos': productos
    })


def listarDetalleCompra(request):
    detalleCompras = DetalleCompra.objects.select_related('producto', 'compra').all()

    return render(request, 'detalleCompra/index.html', {
        'detalleCompras': detalleCompras
    })



