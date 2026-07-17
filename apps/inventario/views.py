from django.shortcuts import render, redirect
from django.contrib import messages
from apps.usuario.decorators import login_requerido, solo_admin
from .models import Inventario
from apps.producto.models import Producto
from django.core.exceptions import ValidationError

@login_requerido
def index(request):
    productos_sin_inventario = Producto.objects.filter(estado=True, inventario__isnull=True)
    if productos_sin_inventario.exists():
        for prod in productos_sin_inventario:
            Inventario.objects.get_or_create(producto=prod)

    inventarios = Inventario.objects.select_related('producto', 'producto__categoria', 'producto__marca').filter(producto__estado=True)
    
    return render(request, 'inventario/index.html', {'inventarios': inventarios})

@solo_admin
def editarInventario(request, id_inventario):
    inventario = Inventario.objects.get(id_inventario=id_inventario)

    if request.method == 'POST':
        try:
            inventario.stock_minimo = int(request.POST.get('stock_minimo', 5))
            inventario.stock_maximo = int(request.POST.get('stock_maximo', 100))
            inventario.ubicacion = request.POST.get('ubicacion', 'Almacén Principal').strip()

            inventario.full_clean()
            inventario.save()
            messages.success(request, "Límites de inventario actualizados exitosamente.")
        except ValidationError as e:
            for field, errors in e.message_dict.items():
                for error in errors:
                    messages.error(request, f"{error}")
        except ValueError:
            messages.error(request, "Los valores de stock mínimo y máximo deben ser números enteros.")
        return redirect('inventario:index')

    return redirect('inventario:index')
