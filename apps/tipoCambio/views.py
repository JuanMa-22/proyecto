from django.shortcuts import render, redirect
from django.http import JsonResponse
from .models import TipoCambio
from apps.producto.models import Producto
from apps.historialPrecio.models import HistorialPrecio
from django.utils import timezone
from decimal import Decimal
from django.contrib import messages
from apps.usuario.decorators import solo_admin
from django.urls import reverse

# Create your views here.
@solo_admin
def index(request):
    inactivos = request.GET.get('inactivos') == 'true'
    if inactivos:
        tipoCambios = TipoCambio.objects.filter(estado=False)
    else:
        tipoCambios = TipoCambio.objects.filter(estado=True)
    return render(request, 'tipoCambio/index.html', {
        'tipoCambios': tipoCambios,
        'mostrar_inactivos': inactivos
    })

@solo_admin
def crearTipoCambio(request):
    if request.method == 'POST':
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
        valor = request.POST['valor']
        fecha = request.POST['fecha']

        try:
            # Desactivar tipos de cambio anteriores
            TipoCambio.objects.filter(estado=True).update(estado=False)

            tipoCambio = TipoCambio(valor=valor, fecha=fecha, estado=True)
            tipoCambio.save()

            # Actualizar todos los productos con el nuevo tipo de cambio
            valor_decimal = Decimal(valor)
            
            productos_activos = Producto.objects.filter(estado=True)
            for producto in productos_activos:
                # Actualizar precio actual
                producto.precio_actual = producto.precio_usd * valor_decimal
                producto.save()

                # Cerrar el historial anterior
                HistorialPrecio.objects.filter(
                    producto=producto,
                    estado=True
                ).update(
                    estado=False,
                    fecha_fin=timezone.now()
                )

                # Crear el nuevo historial
                HistorialPrecio.objects.create(
                    producto=producto,
                    tipo_cambio=tipoCambio,
                    precio_compra=producto.precio_usd,
                    precio_venta=producto.precio_usd * valor_decimal,
                    fecha_inicio=timezone.now(),
                    estado=True
                )

            msg = "Tipo de cambio creado exitosamente y precios actualizados."
            if is_ajax:
                return JsonResponse({'success': True, 'message': msg})
            messages.success(request, msg)
        except Exception as ex:
            msg = f"Error al crear: {str(ex)}"
            if is_ajax:
                return JsonResponse({'success': False, 'message': msg}, status=400)
            messages.error(request, msg)
        return redirect('tipoCambio:index')
    return render(request, 'tipoCambio/crear.html')

@solo_admin
def editarTipoCambio(request, id_tipoCambio):
    tipoCambio = TipoCambio.objects.get(id_tipoCambio=id_tipoCambio)
    if request.method == 'POST':
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
        tipoCambio.valor = request.POST['valor']
        tipoCambio.fecha = request.POST['fecha']
        try:
            tipoCambio.save()

            if tipoCambio.estado:
                valor_decimal = Decimal(tipoCambio.valor)
                
                productos_activos = Producto.objects.filter(estado=True)
                for producto in productos_activos:
                    producto.precio_actual = producto.precio_usd * valor_decimal
                    producto.save()

                    historial = HistorialPrecio.objects.filter(
                        producto=producto,
                        tipo_cambio=tipoCambio,
                        estado=True
                    ).first()
                    if historial:
                        historial.precio_venta = producto.precio_usd * valor_decimal
                        historial.save()

            msg = "Tipo de cambio actualizado exitosamente y precios actualizados."
            if is_ajax:
                return JsonResponse({'success': True, 'message': msg})
            messages.success(request, msg)
        except Exception as ex:
            msg = f"Error al actualizar: {str(ex)}"
            if is_ajax:
                return JsonResponse({'success': False, 'message': msg}, status=400)
            messages.error(request, msg)
        return redirect('tipoCambio:index')
    return render(request, 'tipoCambio/editar.html', {'tipoCambio': tipoCambio})


@solo_admin
def eliminarTipoCambio(request, id_tipoCambio):
    tipoCambio = TipoCambio.objects.get(id_tipoCambio=id_tipoCambio)
    tipoCambio.estado = False
    tipoCambio.save()
    messages.success(request, "Tipo de cambio desactivado exitosamente.")
    return redirect('tipoCambio:index')


@solo_admin
def activarTipoCambio(request, id_tipoCambio):
    # Desactivar tipos de cambio anteriores
    TipoCambio.objects.filter(estado=True).update(estado=False)

    tipoCambio = TipoCambio.objects.get(id_tipoCambio=id_tipoCambio)
    tipoCambio.estado = True
    tipoCambio.save()

    # Actualizar todos los productos con el nuevo tipo de cambio
    valor_decimal = Decimal(tipoCambio.valor)
    productos_activos = Producto.objects.filter(estado=True)
    for producto in productos_activos:
        producto.precio_actual = producto.precio_usd * valor_decimal
        producto.save()

        # Cerrar el historial anterior
        HistorialPrecio.objects.filter(
            producto=producto,
            estado=True
        ).update(
            estado=False,
            fecha_fin=timezone.now()
        )

        # Crear el nuevo historial
        HistorialPrecio.objects.create(
            producto=producto,
            tipo_cambio=tipoCambio,
            precio_compra=producto.precio_usd,
            precio_venta=producto.precio_usd * valor_decimal,
            fecha_inicio=timezone.now(),
            estado=True
        )

    messages.success(request, "Tipo de cambio activado exitosamente y precios actualizados.")
    return redirect(f"{reverse('tipoCambio:index')}?inactivos=true")

