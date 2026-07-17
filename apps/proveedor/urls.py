app_name = 'proveedor'
from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('crear', views.crearProveedor, name='crear'),
    path('editar/<uuid:id_proveedor>', views.editarProveedor, name='editar'),
    path('eliminar/<uuid:id_proveedor>', views.eliminarProveedor, name='eliminar'),
    path('activar/<uuid:id_proveedor>', views.activarProveedor, name='activar'),
]