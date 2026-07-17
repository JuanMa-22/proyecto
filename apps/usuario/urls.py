app_name = 'usuario'
from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('', views.index, name='index'),
    path('crear', views.crearUsuario, name='crear'),
    path('editar/<uuid:id_usuario>', views.editarUsuario, name='editar'),
    path('eliminar/<uuid:id_usuario>', views.eliminarUsuario, name='eliminar'),
    path('activar/<uuid:id_usuario>', views.activarUsuario, name='activar'),
]