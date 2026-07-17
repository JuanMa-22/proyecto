from django.urls import path
from . import views

app_name = 'empresa'

urlpatterns = [
    path('', views.index, name='index'),
    path('crear/', views.crearEmpresa, name='crear'),
    path('editar/<uuid:id_empresa>/', views.editarEmpresa, name='editar'),
    path('guardar-coordenadas/<uuid:id_empresa>/', views.guardarCoordenadas, name='guardar_coordenadas'),
]
