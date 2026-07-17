from django.shortcuts import render, redirect
from .models import HistorialPrecio
from apps.producto.models import Producto
from apps.tipoCambio.models import TipoCambio
from apps.usuario.decorators import solo_admin
from apps.web.reportes_generator import generar_pdf_reporte, generar_excel_reporte

# Create your views here.
@solo_admin
def index(request):
    historialPrecios = HistorialPrecio.objects.select_related('producto', 'tipo_cambio').all()
    return render(request, 'historialPrecio/index.html', {'historialPrecios': historialPrecios})

@solo_admin
def historial_producto(request, id_producto):
    producto = Producto.objects.get(id_producto=id_producto)

    historial = HistorialPrecio.objects.filter(
        producto=producto
    ).order_by('-fecha_inicio')

    return render(request, 'historialPrecio/historial_producto.html', {
        'producto': producto,
        'historial': historial
    })


@solo_admin
def reporte_historial_pdf(request):
    historial = HistorialPrecio.objects.select_related(
        'producto', 'tipo_cambio'
    ).all().order_by('-fecha_inicio')
    headers = ['Producto', 'Tipo Cambio (Bs/$)', 'Precio Compra (USD)', 'Precio Venta (Bs)', 'Fecha Inicio', 'Fecha Fin', 'Estado']
    data = []
    for h in historial:
        fecha_fin = h.fecha_fin.strftime('%d/%m/%Y %H:%M') if h.fecha_fin else '-'
        estado_str = 'Vigente' if h.estado else 'Expirado'
        data.append([
            h.producto.nombre,
            f"{float(h.tipo_cambio.valor):.2f}",
            f"$ {float(h.precio_compra):.2f}",
            f"Bs. {float(h.precio_venta):.2f}",
            h.fecha_inicio.strftime('%d/%m/%Y %H:%M'),
            fecha_fin,
            estado_str
        ])
    return generar_pdf_reporte('Historial de Precios', headers, data, 'reporte_historial_precios.pdf')


@solo_admin
def reporte_historial_excel(request):
    historial = HistorialPrecio.objects.select_related(
        'producto', 'tipo_cambio'
    ).all().order_by('-fecha_inicio')
    headers = ['Producto', 'Tipo Cambio (Bs/$)', 'Precio Compra (USD)', 'Precio Venta (Bs)', 'Fecha Inicio', 'Fecha Fin', 'Estado']
    data = []
    for h in historial:
        fecha_fin = h.fecha_fin.strftime('%d/%m/%Y %H:%M') if h.fecha_fin else '-'
        estado_str = 'Vigente' if h.estado else 'Expirado'
        data.append([
            h.producto.nombre,
            float(h.tipo_cambio.valor),
            float(h.precio_compra),
            float(h.precio_venta),
            h.fecha_inicio.strftime('%d/%m/%Y %H:%M'),
            fecha_fin,
            estado_str
        ])
    return generar_excel_reporte('Historial de Precios', headers, data, 'reporte_historial_precios.xlsx')