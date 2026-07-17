app_name = 'lote'
from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('inicializar/', views.inicializar_lotes_view, name='inicializar'),
    path('detalle/<uuid:id_lote>/', views.detalle_lote, name='detalle'),
]
