app_name = 'cliente'
from django.urls import path
from . import views


urlpatterns = [
    path('', views.index, name='index'),
    path('crear', views.crearCliente, name='crear'),
    path('editar/<uuid:id_cliente>', views.editarCliente, name='editar'),
    path('eliminar/<uuid:id_cliente>', views.eliminarCliente, name='eliminar'),
    path('activar/<uuid:id_cliente>', views.activarCliente, name='activar'),
]