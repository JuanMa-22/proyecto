from django.test import TestCase, Client
from django.urls import reverse
from apps.producto.models import Producto
from apps.categoria.models import Categoria
from apps.marca.models import Marca

class SEOTests(TestCase):
    def setUp(self):
        # Crear datos de prueba
        self.categoria = Categoria.objects.create(
            nombre="Procesadores",
            descripcion="Procesadores de alta calidad",
            estado=True
        )
        self.marca = Marca.objects.create(
            nombre="Intel",
            estado=True
        )
        self.producto = Producto.objects.create(
            nombre="Intel Core i9-13900K",
            descripcion="Procesador Intel de última generación",
            precio_actual=5500.00,
            precio_usd=790.00,
            stock=10,
            categoria=self.categoria,
            marca=self.marca,
            estado=True
        )
        self.client = Client()

    def test_inicio_pagina_seo(self):
        url = reverse('web:inicio_pagina')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<title>SISMEING | Computadoras y Componentes en La Paz</title>")
        self.assertContains(response, 'name="description"')

    def test_detalle_producto_seo(self):
        url = reverse('web:detalle_producto', kwargs={'slug': self.producto.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"<title>{self.producto.nombre} - {self.marca.nombre} en La Paz | SISMEING</title>")
        self.assertContains(response, 'itemCondition')
        self.assertContains(response, 'Intel Core i9-13900K')

    def test_categoria_pagina_seo(self):
        url = reverse('web:categoria_pagina', kwargs={'slug': self.categoria.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"<title>{self.categoria.nombre} en La Paz | SISMEING</title>")
        self.assertContains(response, 'Procesadores')

    def test_sitemap_xml(self):
        response = self.client.get('/sitemap.xml')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/xml')
        # Verificar que contenga el slug de la categoría y del producto
        self.assertContains(response, f"/categorias/{self.categoria.slug}/")
        self.assertContains(response, f"/productos/{self.producto.slug}/")

    def test_robots_txt(self):
        response = self.client.get('/robots.txt')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/plain')
        self.assertContains(response, 'User-agent: *')
        self.assertContains(response, 'Disallow: /admin/')
        self.assertContains(response, 'Sitemap:')

    def test_canonical_url_excludes_get_parameters(self):
        # Enviar petición con parámetros GET
        url = reverse('web:inicio_pagina') + f'?buscar=intel&categoria={self.categoria.id_categoria}&page=2'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # Verificar que el link canonical NO contenga los parámetros GET
        self.assertContains(response, '<link rel="canonical" href="http://testserver/">')
        self.assertNotContains(response, 'buscar=intel')
        self.assertNotContains(response, 'categoria=1')
        self.assertNotContains(response, 'page=2')
