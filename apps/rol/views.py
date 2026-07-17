from django.shortcuts import render, redirect
from .models import Rol
from apps.usuario.decorators import solo_admin
from django.urls import reverse
from django.contrib import messages
from django.http import JsonResponse

# Create your views here.
@solo_admin
def index(request):
    inactivos = request.GET.get('inactivos') == 'true'
    if inactivos:
        roles = Rol.objects.filter(estado=False)
    else:
        roles = Rol.objects.filter(estado=True)
    return render(request, 'rol/index.html', {
        'roles': roles,
        'mostrar_inactivos': inactivos
    })

@solo_admin
def crearRol(request):
    if request.method == 'POST':
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
        nombre = request.POST['nombre']
        estado = True
        rol = Rol(nombre=nombre, estado=estado)
        try:
            rol.full_clean()
            rol.save()
            msg = "Rol creado exitosamente."
            if is_ajax:
                return JsonResponse({'success': True, 'message': msg})
            messages.success(request, msg)
        except Exception as ex:
            msg = f'Error al crear: {str(ex)}'
            if is_ajax:
                return JsonResponse({'success': False, 'message': msg}, status=400)
            messages.error(request, msg)
        return redirect('rol:index')
    return render(request, 'rol/crear.html')

@solo_admin
def editarRol(request, id_rol):
    if request.method == 'POST':
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
        nombre = request.POST['nombre']
        rol = Rol.objects.get(id_rol=id_rol)
        rol.nombre = nombre
        rol.estado = True
        try:
            rol.full_clean()
            rol.save()
            msg = "Rol actualizado exitosamente."
            if is_ajax:
                return JsonResponse({'success': True, 'message': msg})
            messages.success(request, msg)
        except Exception as ex:
            msg = f'Error al actualizar: {str(ex)}'
            if is_ajax:
                return JsonResponse({'success': False, 'message': msg}, status=400)
            messages.error(request, msg)
        return redirect('rol:index')
    rol = Rol.objects.get(id_rol=id_rol)
    return render(request, 'rol/editar.html', {'rol': rol})

@solo_admin
def eliminarRol(request, id_rol):
    rol = Rol.objects.get(id_rol=id_rol)
    rol.estado = False
    rol.save()
    messages.success(request, "Rol desactivado exitosamente.")
    return redirect('rol:index')

@solo_admin
def activarRol(request, id_rol):
    rol = Rol.objects.get(id_rol=id_rol)
    rol.estado = True
    rol.save()
    messages.success(request, "Rol reactivado exitosamente.")
    return redirect(f"{reverse('rol:index')}?inactivos=true")
