from django.shortcuts import render
from django.shortcuts import redirect
from django.http import JsonResponse
from .models import Cliente
from apps.usuario.decorators import login_requerido
from django.urls import reverse
from django.contrib import messages

# Create your views here.

#listar clientes
@login_requerido
def index(request):
    inactivos = request.GET.get('inactivos') == 'true'
    if inactivos:
        clientes = Cliente.objects.filter(estado=False)
    else:
        clientes = Cliente.objects.filter(estado=True)
    return render(request, 'cliente/index.html', {
        'clientes': clientes,
        'mostrar_inactivos': inactivos
    })

@login_requerido
def crearCliente(request):
    if request.method == 'POST':
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('is_ajax') == 'true'
        try:
            nombre     = request.POST['nombre']
            apellido   = request.POST['apellido']
            email      = request.POST.get('email', '')
            telefono   = request.POST['telefono']
            direccion  = request.POST.get('direccion', '')
            ci         = request.POST['ci'].strip()
            estado = True
            
            # Verificar duplicado
            if Cliente.objects.filter(ci=ci).exists():
                raise Exception(f"Ya existe un cliente registrado con el CI/NIT '{ci}'.")
                
            cliente = Cliente(
                nombre=nombre, apellido=apellido, email=email,
                telefono=telefono, direccion=direccion, ci=ci
            )
            cliente.full_clean()
            cliente.save()
            if is_ajax:
                return JsonResponse({
                    'success': True, 
                    'id': str(cliente.id_cliente), 
                    'nombre': f'{cliente.nombre} {cliente.apellido}',
                    'message': "Cliente creado exitosamente."
                })
            messages.success(request, "Cliente creado exitosamente.")
            return redirect('cliente:index')
        except Exception as ex:
            if is_ajax:
                return JsonResponse({'success': False, 'error': str(ex), 'message': str(ex)}, status=400)
            messages.error(request, f'Error: {str(ex)}')
            return redirect('cliente:index')
    return render(request, 'cliente/crear.html')

@login_requerido
def editarCliente(request, id_cliente):
    if request.method == 'POST':
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
        nombre = request.POST['nombre']
        apellido = request.POST['apellido']
        email = request.POST['email']
        telefono = request.POST['telefono']
        direccion = request.POST['direccion']
        ci = request.POST['ci'].strip()
        
        # Verificar duplicado excluyendo al cliente actual
        if Cliente.objects.filter(ci=ci).exclude(id_cliente=id_cliente).exists():
            msg = f"Ya existe otro cliente registrado con el CI/NIT '{ci}'."
            if is_ajax:
                return JsonResponse({'success': False, 'message': msg}, status=400)
            messages.error(request, msg)
            return redirect('cliente:index')
            
        cliente = Cliente.objects.get(id_cliente=id_cliente)
        cliente.nombre = nombre
        cliente.apellido = apellido
        cliente.email = email
        cliente.telefono = telefono
        cliente.direccion = direccion
        cliente.ci = ci
        try:
            cliente.full_clean()
            cliente.save()
            msg = "Cliente actualizado exitosamente."
            if is_ajax:
                return JsonResponse({'success': True, 'message': msg})
            messages.success(request, msg)
        except Exception as ex:
            msg = f'Error al actualizar: {str(ex)}'
            if is_ajax:
                return JsonResponse({'success': False, 'message': msg}, status=400)
            messages.error(request, msg)
        return redirect('cliente:index')
    cliente = Cliente.objects.get(id_cliente=id_cliente)
    return render(request, 'cliente/editar.html', {'cliente': cliente})

@login_requerido
def eliminarCliente(request, id_cliente):
    cliente = Cliente.objects.get(id_cliente=id_cliente)
    cliente.estado = False
    cliente.save()
    messages.success(request, "Cliente desactivado exitosamente.")
    return redirect('cliente:index')

@login_requerido
def activarCliente(request, id_cliente):
    cliente = Cliente.objects.get(id_cliente=id_cliente)
    cliente.estado = True
    cliente.save()
    messages.success(request, "Cliente reactivado exitosamente.")
    return redirect(f"{reverse('cliente:index')}?inactivos=true")
