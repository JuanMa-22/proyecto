from django.shortcuts import render, redirect
from django.db import connection
from .models import Categoria
from apps.usuario.decorators import solo_admin
from django.urls import reverse
from django.contrib import messages
from django.http import JsonResponse

# Create your views here.

@solo_admin
def index(request):
    inactivos = request.GET.get('inactivos') == 'true'
    if inactivos:
        categorias = Categoria.objects.filter(estado=False)
    else:
        categorias = Categoria.objects.filter(estado=True)
    return render(request, 'categoria/index.html', {
        'categorias': categorias,
        'mostrar_inactivos': inactivos
    })

@solo_admin
def crearCategoria(request):
    if request.method == 'POST':
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
        nombre = request.POST['nombre'].strip()
        descripcion = request.POST.get('descripcion', '').strip() or None
        estado = True
        
        if Categoria.objects.filter(nombre__iexact=nombre).exists():
            msg = f"La categoría '{nombre}' ya existe."
            if is_ajax:
                return JsonResponse({'success': False, 'message': msg}, status=400)
            messages.error(request, msg)
            return redirect('categoria:index')
            
        categoria = Categoria(nombre=nombre, descripcion=descripcion, estado=estado)
        categoria.save()
        msg = "Categoría creada exitosamente."
        if is_ajax:
            return JsonResponse({'success': True, 'message': msg})
        messages.success(request, msg)
        return redirect('categoria:index')
    return render(request, 'categoria/crear.html')

@solo_admin
def editarCategoria(request, id_categoria):
    if request.method == 'POST':
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
        nombre = request.POST['nombre'].strip()
        descripcion = request.POST.get('descripcion', '').strip() or None
        
        if Categoria.objects.filter(nombre__iexact=nombre).exclude(id_categoria=id_categoria).exists():
            msg = f"Ya existe otra categoría con el nombre '{nombre}'."
            if is_ajax:
                return JsonResponse({'success': False, 'message': msg}, status=400)
            messages.error(request, msg)
            return redirect('categoria:index')
            
        categoria = Categoria.objects.get(id_categoria=id_categoria)
        categoria.nombre = nombre
        categoria.descripcion = descripcion
        categoria.estado = True
        categoria.save()
        msg = "Categoría actualizada exitosamente."
        if is_ajax:
            return JsonResponse({'success': True, 'message': msg})
        messages.success(request, msg)
        return redirect('categoria:index')
    categoria = Categoria.objects.get(id_categoria=id_categoria)
    return render(request, 'categoria/editar.html', {'categoria': categoria})


@solo_admin
def eliminarCategoria(request, id_categoria):
    categoria = Categoria.objects.get(id_categoria=id_categoria)
    categoria.estado = False
    categoria.save()
    messages.success(request, "Categoría desactivada exitosamente.")
    return redirect('categoria:index')

@solo_admin
def activarCategoria(request, id_categoria):
    categoria = Categoria.objects.get(id_categoria=id_categoria)
    categoria.estado = True
    categoria.save()
    messages.success(request, "Categoría reactivada exitosamente.")
    return redirect(f"{reverse('categoria:index')}?inactivos=true")
