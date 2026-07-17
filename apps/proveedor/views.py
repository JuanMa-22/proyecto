from django.shortcuts import render, redirect
from django.http import JsonResponse
from .models import Proveedor
from apps.usuario.decorators import solo_admin
from django.urls import reverse
from django.contrib import messages

@solo_admin
def index(request):
    inactivos = request.GET.get('inactivos') == 'true'
    if inactivos:
        proveedores = Proveedor.objects.filter(estado=False)
    else:
        proveedores = Proveedor.objects.filter(estado=True)
    return render(request, 'proveedor/index.html', {
        'proveedores': proveedores,
        'mostrar_inactivos': inactivos
    })

@solo_admin
def crearProveedor(request):
    if request.method == 'POST':
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('is_ajax') == 'true'
        try:
            nombre   = request.POST['nombre'].strip()
            telefono = request.POST['telefono']
            estado   = True
            
            # Verificar duplicado
            if Proveedor.objects.filter(nombre__iexact=nombre).exists():
                raise Exception(f"El proveedor '{nombre}' ya existe.")
                
            proveedor = Proveedor(nombre=nombre, telefono=telefono, estado=estado)
            proveedor.full_clean()
            proveedor.save()
            if is_ajax:
                return JsonResponse({
                    'success': True, 
                    'id': str(proveedor.id_proveedor), 
                    'nombre': proveedor.nombre,
                    'message': "Proveedor creado exitosamente."
                })
            messages.success(request, "Proveedor creado exitosamente.")
            return redirect('proveedor:index')
        except Exception as ex:
            if is_ajax:
                return JsonResponse({'success': False, 'error': str(ex), 'message': str(ex)}, status=400)
            messages.error(request, f'Error al crear proveedor: {str(ex)}')
            return redirect('proveedor:index')
    return render(request, 'proveedor/crear.html')

@solo_admin
def editarProveedor(request, id_proveedor):
    if request.method == 'POST':
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
        nombre = request.POST['nombre'].strip()
        telefono = request.POST['telefono']
        
        # Verificar duplicado excluyendo el actual
        if Proveedor.objects.filter(nombre__iexact=nombre).exclude(id_proveedor=id_proveedor).exists():
            msg = f"Ya existe otro proveedor con el nombre '{nombre}'."
            if is_ajax:
                return JsonResponse({'success': False, 'message': msg}, status=400)
            messages.error(request, msg)
            return redirect('proveedor:index')
            
        proveedor = Proveedor.objects.get(id_proveedor=id_proveedor)
        proveedor.nombre = nombre
        proveedor.telefono = telefono
        try:
            proveedor.full_clean()
            proveedor.save()
            msg = "Proveedor actualizado exitosamente."
            if is_ajax:
                return JsonResponse({'success': True, 'message': msg})
            messages.success(request, msg)
        except Exception as ex:
            msg = f'Error al actualizar: {str(ex)}'
            if is_ajax:
                return JsonResponse({'success': False, 'message': msg}, status=400)
            messages.error(request, msg)
        return redirect('proveedor:index')
    proveedor = Proveedor.objects.get(id_proveedor=id_proveedor)
    return render(request, 'proveedor/editar.html', {'proveedor': proveedor})

@solo_admin
def eliminarProveedor(request, id_proveedor):
    proveedor = Proveedor.objects.get(id_proveedor=id_proveedor)
    proveedor.estado = False
    proveedor.save()
    messages.success(request, "Proveedor desactivado exitosamente.")
    return redirect('proveedor:index')

@solo_admin
def activarProveedor(request, id_proveedor):
    proveedor = Proveedor.objects.get(id_proveedor=id_proveedor)
    proveedor.estado = True
    proveedor.save()
    messages.success(request, "Proveedor reactivado exitosamente.")
    return redirect(f"{reverse('proveedor:index')}?inactivos=true")
