app_name = 'compra'
from django.urls import path
from . import views


urlpatterns = [
    path('', views.index, name='index'),
    path('crear', views.crearCompra, name='crear'),
    path('agregar_detalle', views.agregar_detalle_compra, name='agregar_detalle'),
    path('reportes/', views.reporte_compra_view, name='reportes'),
    path('reportes/pdf', views.reporte_compra_pdf, name='reporte_pdf'),
    path('reportes/excel', views.reporte_compra_excel, name='reporte_excel'),
]