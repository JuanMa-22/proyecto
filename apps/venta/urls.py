app_name = 'venta'
from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('crear', views.crearVenta, name='crear'),
    path('agregar_detalle', views.agregar_detalle_venta, name='agregar_detalle'),
    path('recibo/<uuid:id_venta>', views.recibo_venta, name='recibo_venta'),
    path('reportes/', views.reporte_venta_view, name='reportes'),
    path('reportes/pdf', views.reporte_venta_pdf, name='reporte_pdf'),
    path('reportes/excel', views.reporte_venta_excel, name='reporte_excel'),
]