app_name = 'detalleCompra'
from django.urls import path
from . import views

urlpatterns = [
    path('agregar', views.agregarDetalleCompra, name='agregar'),
    path('listar', views.listarDetalleCompra, name='listar'),

]