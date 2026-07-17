from django.urls import path
from . import views

app_name = 'inventario'

urlpatterns = [
    path('', views.index, name='index'),
    path('editar/<uuid:id_inventario>/', views.editarInventario, name='editar'),
]
