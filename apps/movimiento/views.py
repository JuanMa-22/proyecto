from django.shortcuts import render
from .models import Movimiento
from apps.producto.models import Producto
from apps.usuario.decorators import login_requerido
from apps.web.reportes_generator import generar_pdf_reporte, generar_excel_reporte

@login_requerido
def index(request):
    movimientos = Movimiento.objects.select_related(
        'producto', 'tipoMovimiento'
    ).all()

    return render(request, 'movimiento/index.html', {
        'movimientos': movimientos
    })


@login_requerido
def movimientos_producto(request, id_producto):
    producto = Producto.objects.get(id_producto=id_producto)
    movimientos = Movimiento.objects.filter(
        producto=producto
    ).order_by('-fecha')

    return render(request, 'movimiento/producto.html', {
        'producto': producto,
        'movimientos': movimientos
    })


@login_requerido
def reporte_movimientos_pdf(request):
    movimientos = Movimiento.objects.select_related(
        'producto', 'tipoMovimiento'
    ).all().order_by('-fecha')
    headers = ['Fecha', 'Producto', 'Tipo', 'Cantidad', 'Stock Anterior', 'Stock Actual', 'Motivo']
    data = []
    for m in movimientos:
        data.append([
            m.fecha.strftime('%d/%m/%Y %H:%M'),
            m.producto.nombre,
            m.tipoMovimiento.nombre,
            m.cantidad,
            m.stock_anterior,
            m.stock_actual,
            m.motivo or '-'
        ])
    return generar_pdf_reporte('Movimientos de Inventario', headers, data, 'reporte_movimientos.pdf')


@login_requerido
def reporte_movimientos_excel(request):
    movimientos = Movimiento.objects.select_related(
        'producto', 'tipoMovimiento'
    ).all().order_by('-fecha')
    headers = ['Fecha', 'Producto', 'Tipo', 'Cantidad', 'Stock Anterior', 'Stock Actual', 'Motivo']
    data = []
    for m in movimientos:
        data.append([
            m.fecha.strftime('%d/%m/%Y %H:%M'),
            m.producto.nombre,
            m.tipoMovimiento.nombre,
            m.cantidad,
            m.stock_anterior,
            m.stock_actual,
            m.motivo or '-'
        ])
    return generar_excel_reporte('Movimientos de Inventario', headers, data, 'reporte_movimientos.xlsx')