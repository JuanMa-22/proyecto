app_name = 'tipoCambio'
from django.urls import path
from . import views


urlpatterns = [
    path('', views.index, name='index'),
    path('crear', views.crearTipoCambio, name='crear'),
    path('editar/<uuid:id_tipoCambio>', views.editarTipoCambio, name='editar'),
    path('eliminar/<uuid:id_tipoCambio>', views.eliminarTipoCambio, name='eliminar'),
    path('activar/<uuid:id_tipoCambio>', views.activarTipoCambio, name='activar'),
]