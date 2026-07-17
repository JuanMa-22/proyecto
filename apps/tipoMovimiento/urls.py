app_name = 'tipoMovimiento'
from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('crear', views.crearTipoMovimiento, name='crear'),
    path('editar/<uuid:id_tipoMovimiento>', views.editarTipoMovimiento, name='editar'),
    path('eliminar/<uuid:id_tipoMovimiento>', views.eliminarTipoMovimiento, name='eliminar'),
    path('activar/<uuid:id_tipoMovimiento>', views.activarTipoMovimiento, name='activar'),
]