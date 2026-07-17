"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap
from apps.web.sitemaps import StaticViewSitemap, CategoriaSitemap, ProductoSitemap
from apps.web.views import robots_txt

sitemaps = {
    'static': StaticViewSitemap,
    'categorias': CategoriaSitemap,
    'productos': ProductoSitemap,
}

urlpatterns = [
    path('admin/', admin.site.urls),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('robots.txt', robots_txt, name='robots_txt'),
    path('', include('apps.web.urls')),
    path('productos/', include('apps.producto.urls')),
    path('categorias/', include('apps.categoria.urls')),
    path('clientes/', include('apps.cliente.urls')),
    path('marcas/', include('apps.marca.urls')),
    path('proveedores/', include('apps.proveedor.urls')),
    path('roles/', include('apps.rol.urls')),
    path('tipocambios/', include('apps.tipoCambio.urls')),
    path('usuarios/', include('apps.usuario.urls')),
    path('ventas/', include('apps.venta.urls')),
    path('compras/', include('apps.compra.urls')),
    path('movimientos/', include('apps.movimiento.urls')),
    path('historialprecios/', include('apps.historialPrecio.urls')),
    path('tipomovimientos/', include('apps.tipoMovimiento.urls')),
    path('agente-conversacional/', include('apps.agenteConversacional.urls', namespace='agenteConversacional')),
    path('empresa/', include('apps.empresa.urls')),
    path('inventario/', include('apps.inventario.urls')),
    path('lotes/', include('apps.lote.urls', namespace='lote')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
