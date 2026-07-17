app_name = 'categoria'
from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('crear', views.crearCategoria, name='crear'),
    path('editar/<uuid:id_categoria>', views.editarCategoria, name='editar'),
    path('eliminar/<uuid:id_categoria>', views.eliminarCategoria, name='eliminar'),
    path('activar/<uuid:id_categoria>', views.activarCategoria, name='activar'),
]