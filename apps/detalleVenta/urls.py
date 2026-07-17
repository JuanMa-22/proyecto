app_name = 'detalleVenta'
from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('crear', views.crearDetalleVenta, name='crear'),
            
]