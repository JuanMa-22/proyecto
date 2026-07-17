from functools import wraps
from django.shortcuts import redirect, render
from django.contrib import messages
from apps.usuario.models import Usuario

# ─────────────────────────────────────────────
# Helpers de sesión
# ─────────────────────────────────────────────

def obtener_rol_sesion(request):
    """Devuelve el nombre del rol del usuario logueado (en minúsculas) o cadena vacía."""
    return str(request.session.get('usuario_rol', '')).strip().lower()


def es_admin(request):
    """Retorna True si el usuario logueado NO tiene rol 'vendedor'."""
    rol = obtener_rol_sesion(request)
    return rol != 'vendedor'


def es_vendedor(request):
    """Retorna True si el usuario logueado tiene rol 'vendedor'."""
    rol = obtener_rol_sesion(request)
    return rol == 'vendedor'


# ─────────────────────────────────────────────
# Decoradores Seguros (Validan contra DB en cada request)
# ─────────────────────────────────────────────

def login_requerido(view_func):
    """
    Redirige al login si no hay sesión activa o si el usuario está inactivo/eliminado.
    """
    @wraps(view_func)
    def _wrapper(request, *args, **kwargs):
        usuario_id = request.session.get('usuario_id')
        if not usuario_id:
            return redirect('usuario:login')
            
        try:
            usuario = Usuario.objects.select_related('rol').get(pk=usuario_id, estado=True)
            # Sincronizar el rol en la sesión por si cambió en DB
            request.session['usuario_rol'] = str(usuario.rol)
        except Usuario.DoesNotExist:
            request.session.flush()
            return redirect('usuario:login')
            
        return view_func(request, *args, **kwargs)
    return _wrapper


def solo_admin(view_func):
    """
    Permite el acceso solo a usuarios con rol distinto de 'vendedor' (Administrador).
    Valida estado y rol en base de datos en tiempo real.
    """
    @wraps(view_func)
    def _wrapper(request, *args, **kwargs):
        usuario_id = request.session.get('usuario_id')
        if not usuario_id:
            return redirect('usuario:login')
            
        try:
            usuario = Usuario.objects.select_related('rol').get(pk=usuario_id, estado=True)
            request.session['usuario_rol'] = str(usuario.rol)
            if usuario.rol.nombre.lower() == 'vendedor':
                return render(request, 'layout/acceso_denegado.html', status=403)
        except Usuario.DoesNotExist:
            request.session.flush()
            return redirect('usuario:login')
            
        return view_func(request, *args, **kwargs)
    return _wrapper
