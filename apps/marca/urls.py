app_name = 'marca'
from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('crear', views.crearMarca, name='crear'),
    path('editar/<uuid:id_marca>', views.editarMarca, name='editar'),
    path('eliminar/<uuid:id_marca>', views.eliminarMarca, name='eliminar'),
    path('activar/<uuid:id_marca>', views.activarMarca, name='activar'),
]