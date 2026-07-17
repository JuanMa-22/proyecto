app_name = 'producto'
from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('crear', views.crearProducto, name='crear'),
    path('editar/<uuid:id_producto>', views.editarProducto, name='editar'),
    path('eliminar/<uuid:id_producto>', views.eliminarProducto, name='eliminar'),
    path('activar/<uuid:id_producto>', views.activarProducto, name='activar'),
    path('especificaciones/<uuid:id_producto>', views.especificacionesProducto, name='especificaciones'),
    path('reporte/pdf', views.reporte_productos_pdf, name='reporte_pdf'),
    path('reporte/excel', views.reporte_productos_excel, name='reporte_excel'),
]