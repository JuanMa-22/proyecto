app_name = 'rol'
from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('crear', views.crearRol, name='crear'),
    path('editar/<uuid:id_rol>', views.editarRol, name='editar'),
    path('eliminar/<uuid:id_rol>', views.eliminarRol, name='eliminar'),
    path('activar/<uuid:id_rol>', views.activarRol, name='activar'),
]