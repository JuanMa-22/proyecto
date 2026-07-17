from django.shortcuts import render, redirect
from .models import Marca
from apps.usuario.decorators import solo_admin
from django.urls import reverse
from django.contrib import messages
from django.http import JsonResponse

# Create your views here.
@solo_admin
def index(request):
    inactivos = request.GET.get('inactivos') == 'true'
    if inactivos:
        marcas = Marca.objects.filter(estado=False)
    else:
        marcas = Marca.objects.filter(estado=True)
    return render(request, 'marca/index.html', {
        'marcas': marcas,
        'mostrar_inactivos': inactivos
    })
    
@solo_admin
def crearMarca(request):
    if request.method == 'POST':
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
        nombre = request.POST['nombre'].strip()
        descripcion = request.POST.get('descripcion', '').strip() or None
        estado = True
        
        if Marca.objects.filter(nombre__iexact=nombre).exists():
            msg = f"La marca '{nombre}' ya existe."
            if is_ajax:
                return JsonResponse({'success': False, 'message': msg}, status=400)
            messages.error(request, msg)
            return redirect('marca:index')
            
        marca = Marca(nombre=nombre, descripcion=descripcion, estado=estado)
        marca.save()
        msg = "Marca creada exitosamente."
        if is_ajax:
            return JsonResponse({'success': True, 'message': msg})
        messages.success(request, msg)
        return redirect('marca:index')
    return render(request, 'marca/crear.html')

@solo_admin
def editarMarca(request, id_marca):
    if request.method == 'POST':
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
        nombre = request.POST['nombre'].strip()
        descripcion = request.POST.get('descripcion', '').strip() or None
        
        if Marca.objects.filter(nombre__iexact=nombre).exclude(id_marca=id_marca).exists():
            msg = f"Ya existe otra marca con el nombre '{nombre}'."
            if is_ajax:
                return JsonResponse({'success': False, 'message': msg}, status=400)
            messages.error(request, msg)
            return redirect('marca:index')
            
        marca = Marca.objects.get(id_marca=id_marca)
        marca.nombre = nombre
        marca.descripcion = descripcion
        marca.estado = True
        marca.save()
        msg = "Marca actualizada exitosamente."
        if is_ajax:
            return JsonResponse({'success': True, 'message': msg})
        messages.success(request, msg)
        return redirect('marca:index')
    marca = Marca.objects.get(id_marca=id_marca)
    return render(request, 'marca/editar.html', {'marca': marca})

@solo_admin
def eliminarMarca(request, id_marca):
    marca = Marca.objects.get(id_marca=id_marca)
    marca.estado = False
    marca.save()
    messages.success(request, "Marca desactivada exitosamente.")
    return redirect('marca:index')

@solo_admin
def activarMarca(request, id_marca):
    marca = Marca.objects.get(id_marca=id_marca)
    marca.estado = True
    marca.save()
    messages.success(request, "Marca reactivada exitosamente.")
    return redirect(f"{reverse('marca:index')}?inactivos=true")