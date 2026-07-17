from django.contrib import admin
from .models import Usuario, IntentoLogin

@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'nombre', 'apellido', 'email', 'rol', 'estado', 'created_at')
    list_filter = ('rol', 'estado')
    search_fields = ('usuario', 'nombre', 'apellido', 'email')

@admin.register(IntentoLogin)
class IntentoLoginAdmin(admin.ModelAdmin):
    list_display = ('usuario_ingresado', 'ip_origen', 'cantidad_intentos', 'bloqueado_hasta', 'ultimo_intento')
    list_filter = ('bloqueado_hasta', 'ultimo_intento')
    search_fields = ('usuario_ingresado', 'ip_origen')
    readonly_fields = ('usuario_ingresado', 'ip_origen', 'cantidad_intentos', 'bloqueado_hasta', 'ultimo_intento', 'created_at', 'updated_at')
