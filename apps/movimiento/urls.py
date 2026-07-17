app_name = 'movimiento'
from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('producto/<uuid:id_producto>', views.movimientos_producto, name='producto'),
    path('reporte/pdf', views.reporte_movimientos_pdf, name='reporte_pdf'),
    path('reporte/excel', views.reporte_movimientos_excel, name='reporte_excel'),
]