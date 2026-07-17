from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.hashers import make_password, check_password
from django.contrib import messages
from .models import Usuario
from apps.rol.models import Rol
from .decorators import login_requerido, solo_admin
from django.urls import reverse

# ─────────────────── Autenticación ───────────────────
from django.utils import timezone
from datetime import timedelta
from .models import Usuario, IntentoLogin

def obtener_ip_cliente(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
    return ip

# ─────────────────── Autenticación ───────────────────
def login_view(request):
    if request.session.get('usuario_id'):
        return redirect('web:dashboard')
    
    error = None
    ip = obtener_ip_cliente(request)
    
    if request.method == 'POST':
        usuario_input = request.POST.get('usuario', '').strip()
        password_input = request.POST.get('password', '')
        
        ahora = timezone.now()
        
        # 1. Comprobar si está bloqueado por IP y Nombre de Usuario
        intento_registro, _ = IntentoLogin.objects.get_or_create(
            usuario_ingresado=usuario_input,
            ip_origen=ip
        )
        
        if intento_registro.bloqueado_hasta and intento_registro.bloqueado_hasta > ahora:
            restante = intento_registro.bloqueado_hasta - ahora
            minutos = int(restante.total_seconds() / 60) + 1
            error = f"Se realizaron varios intentos de inicio de sesión. Inténtalo nuevamente más tarde. (Bloqueado por {minutos} min)"
            return render(request, 'login/login.html', {'error': error})
            
        try:
            usuario = Usuario.objects.get(usuario=usuario_input, estado=True)
            if check_password(password_input, usuario.password):
                # Login correcto -> reiniciar intentos
                intento_registro.cantidad_intentos = 0
                intento_registro.bloqueado_hasta = None
                intento_registro.save()
                
                request.session['usuario_id']     = str(usuario.id_usuario)
                request.session['usuario_nombre'] = f'{usuario.nombre} {usuario.apellido}'
                request.session['usuario_rol']    = str(usuario.rol)
                return redirect('web:dashboard')
            else:
                # Contraseña incorrecta
                intento_registro.cantidad_intentos += 1
                if intento_registro.cantidad_intentos >= 5:
                    intento_registro.bloqueado_hasta = ahora + timedelta(minutes=15)
                intento_registro.save()
                error = 'Usuario o contraseña incorrectos.'
        except Usuario.DoesNotExist:
            # Usuario no existe o inactivo
            intento_registro.cantidad_intentos += 1
            if intento_registro.cantidad_intentos >= 5:
                intento_registro.bloqueado_hasta = ahora + timedelta(minutes=15)
            intento_registro.save()
            error = 'Usuario o contraseña incorrectos.'
            
    return render(request, 'login/login.html', {'error': error})

def logout_view(request):
    request.session.flush()
    return redirect('usuario:login')

# ─────────────────── CRUD Usuarios ───────────────────
@solo_admin
def index(request):
    inactivos = request.GET.get('inactivos') == 'true'
    if inactivos:
        usuarios = Usuario.objects.filter(estado=False)
    else:
        usuarios = Usuario.objects.filter(estado=True)
    roles = Rol.objects.filter(estado=True)
    return render(request, 'usuario/index.html', {
        'usuarios': usuarios, 
        'roles': roles,
        'mostrar_inactivos': inactivos
    })


@solo_admin
def crearUsuario(request):
    if request.method == 'POST':
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
        nombre = request.POST['nombre']
        apellido = request.POST['apellido']
        email = request.POST['email']
        telefono = request.POST['telefono']
        direccion = request.POST['direccion']
        ci = request.POST['ci'].strip()
        usuario_name = request.POST['usuario'].strip()
        
        # Check duplicate username
        if Usuario.objects.filter(usuario__iexact=usuario_name).exists():
            msg = f"El nombre de usuario '{usuario_name}' ya existe."
            if is_ajax:
                return JsonResponse({'success': False, 'message': msg}, status=400)
            messages.error(request, msg)
            return redirect('usuario:index')
            
        # Check duplicate CI
        if Usuario.objects.filter(ci=ci).exists():
            msg = f"Ya existe un usuario registrado con el CI '{ci}'."
            if is_ajax:
                return JsonResponse({'success': False, 'message': msg}, status=400)
            messages.error(request, msg)
            return redirect('usuario:index')
            
        password_raw = request.POST['password']
        
        # Validar fortaleza de la contraseña (mínimo 8 caracteres, letras y números)
        import re
        if (len(password_raw) < 8 or 
            not re.search(r'[a-zA-ZáéíóúÁÉÍÓÚñÑ]', password_raw) or 
            not re.search(r'[0-9]', password_raw)):
            msg = "La contraseña debe tener al menos 8 caracteres y contener letras y números."
            if is_ajax:
                return JsonResponse({'success': False, 'message': msg}, status=400)
            messages.error(request, msg)
            return redirect('usuario:index')
            
        password = make_password(password_raw)
        rol = Rol.objects.get(id_rol=request.POST['rol'])
        estado = True
        usuario = Usuario(nombre=nombre, apellido=apellido, email=email, telefono=telefono,
                          direccion=direccion, ci=ci, usuario=usuario_name,
                          password=password, rol=rol, estado=estado)
        try:
            usuario.full_clean()
            usuario.save()
            msg = "Usuario creado exitosamente."
            if is_ajax:
                return JsonResponse({'success': True, 'message': msg})
            messages.success(request, msg)
        except Exception as ex:
            msg = f'Error al crear: {str(ex)}'
            if is_ajax:
                return JsonResponse({'success': False, 'message': msg}, status=400)
            messages.error(request, msg)
        return redirect('usuario:index')
    roles = Rol.objects.filter(estado=True)
    return render(request, 'usuario/crear.html', {'roles': roles})

@solo_admin
def editarUsuario(request, id_usuario):
    if request.method == 'POST':
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
        nombre = request.POST['nombre']
        apellido = request.POST['apellido']
        email = request.POST['email']
        telefono = request.POST['telefono']
        direccion = request.POST['direccion']
        ci = request.POST['ci'].strip()
        usuario_name = request.POST['usuario'].strip()
        
        # Check duplicate username excluding current user
        if Usuario.objects.filter(usuario__iexact=usuario_name).exclude(id_usuario=id_usuario).exists():
            msg = f"El nombre de usuario '{usuario_name}' ya está en uso por otro usuario."
            if is_ajax:
                return JsonResponse({'success': False, 'message': msg}, status=400)
            messages.error(request, msg)
            return redirect('usuario:index')
            
        # Check duplicate CI excluding current user
        if Usuario.objects.filter(ci=ci).exclude(id_usuario=id_usuario).exists():
            msg = f"Ya existe otro usuario registrado con el CI '{ci}'."
            if is_ajax:
                return JsonResponse({'success': False, 'message': msg}, status=400)
            messages.error(request, msg)
            return redirect('usuario:index')
            
        rol = Rol.objects.get(id_rol=request.POST['rol'])
        estado = True
        usuario = Usuario.objects.get(id_usuario=id_usuario)
        usuario.nombre = nombre
        usuario.apellido = apellido
        usuario.email = email
        usuario.telefono = telefono
        usuario.direccion = direccion
        usuario.ci = ci
        usuario.usuario = usuario_name
        
        password_raw = request.POST.get('password', '').strip()
        if password_raw:
            # Validar nueva contraseña
            import re
            if (len(password_raw) < 8 or 
                not re.search(r'[a-zA-ZáéíóúÁÉÍÓÚñÑ]', password_raw) or 
                not re.search(r'[0-9]', password_raw)):
                msg = "La contraseña debe tener al menos 8 caracteres y contener letras y números."
                if is_ajax:
                    return JsonResponse({'success': False, 'message': msg}, status=400)
                messages.error(request, msg)
                return redirect('usuario:index')
            usuario.password = make_password(password_raw)

        usuario.rol = rol
        usuario.estado = estado
        try:
            usuario.full_clean()
            usuario.save()
            msg = "Usuario actualizado exitosamente."
            if is_ajax:
                return JsonResponse({'success': True, 'message': msg})
            messages.success(request, msg)
        except Exception as ex:
            msg = f'Error al actualizar: {str(ex)}'
            if is_ajax:
                return JsonResponse({'success': False, 'message': msg}, status=400)
            messages.error(request, msg)
        return redirect('usuario:index')
    usuario = Usuario.objects.get(id_usuario=id_usuario)
    return render(request, 'usuario/editar.html', {'usuario': usuario})

@solo_admin
def eliminarUsuario(request, id_usuario):
    usuario = Usuario.objects.get(id_usuario=id_usuario)
    usuario.estado = False
    usuario.save()
    messages.success(request, "Usuario desactivado exitosamente.")
    return redirect('usuario:index')

@solo_admin
def activarUsuario(request, id_usuario):
    usuario = Usuario.objects.get(id_usuario=id_usuario)
    usuario.estado = True
    usuario.save()
    messages.success(request, "Usuario reactivado exitosamente.")
    return redirect(f"{reverse('usuario:index')}?inactivos=true")
