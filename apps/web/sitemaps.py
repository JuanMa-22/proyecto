from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from apps.producto.models import Producto
from apps.categoria.models import Categoria

class StaticViewSitemap(Sitemap):
    priority = 0.8
    changefreq = 'weekly'

    def items(self):
        return ['web:inicio_pagina', 'web:nosotros_pagina', 'web:servicios_pagina', 'web:ubicacion_pagina']

    def location(self, item):
        return reverse(item)

class CategoriaSitemap(Sitemap):
    priority = 0.7
    changefreq = 'weekly'

    def items(self):
        return Categoria.objects.filter(estado=True).order_by('nombre')

    def location(self, item):
        return reverse('web:categoria_pagina', kwargs={'slug': item.slug})

class ProductoSitemap(Sitemap):
    priority = 0.9
    changefreq = 'daily'

    def items(self):
        return Producto.objects.filter(estado=True, stock__gt=0).order_by('nombre')

    def location(self, item):
        return reverse('web:detalle_producto', kwargs={'slug': item.slug})
