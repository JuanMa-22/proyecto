from django.shortcuts import render, redirect
from .models import tipoMovimiento
from apps.usuario.decorators import solo_admin
from django.urls import reverse
from django.contrib import messages
from django.http import JsonResponse

# Create your views here.
@solo_admin
def index(request):
    inactivos = request.GET.get('inactivos') == 'true'
    if inactivos:
        tiposMovimientos = tipoMovimiento.objects.filter(estado=False)
    else:
        tiposMovimientos = tipoMovimiento.objects.filter(estado=True)
    return render(request, 'tipoMovimiento/index.html', {
        'tiposMovimientos': tiposMovimientos,
        'mostrar_inactivos': inactivos
    })

@solo_admin
def crearTipoMovimiento(request):
    if request.method == 'POST':
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
        nombre = request.POST['nombre']
        estado = True
        obj_movimiento = tipoMovimiento(nombre=nombre, estado=estado)
        try:
            obj_movimiento.full_clean()
            obj_movimiento.save()
            msg = "Tipo de movimiento creado exitosamente."
            if is_ajax:
                return JsonResponse({'success': True, 'message': msg})
            messages.success(request, msg)
        except Exception as ex:
            msg = f"Error al crear: {str(ex)}"
            if is_ajax:
                return JsonResponse({'success': False, 'message': msg}, status=400)
            messages.error(request, msg)
        return redirect('tipoMovimiento:index')
    return render(request, 'tipoMovimiento/crear.html')

@solo_admin
def editarTipoMovimiento(request, id_tipoMovimiento):
    if request.method == 'POST':
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
        nombre = request.POST['nombre']
        obj_movimiento = tipoMovimiento.objects.get(id_tipoMovimiento=id_tipoMovimiento)
        obj_movimiento.nombre = nombre
        obj_movimiento.estado = True
        try:
            obj_movimiento.full_clean()
            obj_movimiento.save()
            msg = "Tipo de movimiento actualizado exitosamente."
            if is_ajax:
                return JsonResponse({'success': True, 'message': msg})
            messages.success(request, msg)
        except Exception as ex:
            msg = f"Error al actualizar: {str(ex)}"
            if is_ajax:
                return JsonResponse({'success': False, 'message': msg}, status=400)
            messages.error(request, msg)
        return redirect('tipoMovimiento:index')
    obj_movimiento = tipoMovimiento.objects.get(id_tipoMovimiento=id_tipoMovimiento)
    return render(request, 'tipoMovimiento/editar.html', {'tipoMovimiento': obj_movimiento})
    
@solo_admin
def eliminarTipoMovimiento(request, id_tipoMovimiento):
    obj_movimiento = tipoMovimiento.objects.get(id_tipoMovimiento=id_tipoMovimiento)
    obj_movimiento.estado = False
    obj_movimiento.save()
    messages.success(request, "Tipo de movimiento desactivado exitosamente.")
    return redirect('tipoMovimiento:index')

@solo_admin
def activarTipoMovimiento(request, id_tipoMovimiento):
    obj_movimiento = tipoMovimiento.objects.get(id_tipoMovimiento=id_tipoMovimiento)
    obj_movimiento.estado = True
    obj_movimiento.save()
    messages.success(request, "Tipo de movimiento reactivado exitosamente.")
    return redirect(f"{reverse('tipoMovimiento:index')}?inactivos=true")
