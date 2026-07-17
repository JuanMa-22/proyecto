app_name = 'historialPrecio'
from django.urls import path
from . import views

urlpatterns = [
    path('index', views.index, name='index'),
    path('<int:id_producto>', views.historial_producto, name='historial_producto'),
    path('reporte/pdf', views.reporte_historial_pdf, name='reporte_pdf'),
    path('reporte/excel', views.reporte_historial_excel, name='reporte_excel'),
]