from django.test import TestCase, Client
from django.urls import reverse
from apps.usuario.models import Usuario, IntentoLogin
from apps.rol.models import Rol
from apps.cliente.models import Cliente
from apps.proveedor.models import Proveedor
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest.mock import patch
from apps.categoria.models import Categoria
from apps.marca.models import Marca
from apps.tipoCambio.models import TipoCambio
from apps.producto.models import Producto
from apps.venta.models import Venta
from apps.compra.models import Compra
from django.utils import timezone
from decimal import Decimal
from PIL import Image
import io

class UsuarioPasswordValidationTests(TestCase):
    def setUp(self):
        # Crear rol Administrador
        self.rol_admin, _ = Rol.objects.get_or_create(nombre="Administrador")
        
        # Crear un usuario administrador para la sesión
        self.admin_user = Usuario.objects.create(
            nombre="Admin",
            apellido="Test",
            email="admin@test.com",
            telefono="123456",
            direccion="Test Dir",
            ci="87654321",
            usuario="admin_test",
            password="somepasswordhash",
            rol=self.rol_admin,
            estado=True
        )
        
        self.client = Client()
        # Iniciar sesión simulada usando variables de sesión requeridas por el decorador
        session = self.client.session
        session['usuario_id'] = str(self.admin_user.id_usuario)
        session['usuario_nombre'] = "Admin Test"
        session['usuario_rol'] = "Administrador"
        session.save()

    def test_crear_usuario_password_valido(self):
        url = reverse('usuario:crear')
        data = {
            'nombre': 'Nuevo',
            'apellido': 'Usuario',
            'email': 'nuevo@test.com',
            'telefono': '987654',
            'direccion': 'Direccion',
            'ci': '123456',
            'usuario': 'new_user',
            'password': 'SecurePassword123',
            'rol': self.rol_admin.id_rol
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)  # Debe redireccionar exitosamente
        self.assertTrue(Usuario.objects.filter(usuario='new_user').exists())

    def test_crear_usuario_password_corto(self):
        url = reverse('usuario:crear')
        data = {
            'nombre': 'Nuevo',
            'apellido': 'Usuario',
            'email': 'nuevo@test.com',
            'telefono': '987654',
            'direccion': 'Direccion',
            'ci': '1234567',
            'usuario': 'new_user_short',
            'password': 'S123',  # Menos de 8 caracteres
            'rol': self.rol_admin.id_rol
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        # No debe haberse creado el usuario
        self.assertFalse(Usuario.objects.filter(usuario='new_user_short').exists())

    def test_crear_usuario_password_sin_letras(self):
        url = reverse('usuario:crear')
        data = {
            'nombre': 'Nuevo',
            'apellido': 'Usuario',
            'email': 'nuevo@test.com',
            'telefono': '987654',
            'direccion': 'Direccion',
            'ci': '12345678',
            'usuario': 'new_user_no_letters',
            'password': '1234567890',  # Solo números
            'rol': self.rol_admin.id_rol
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Usuario.objects.filter(usuario='new_user_no_letters').exists())

    def test_crear_usuario_password_sin_numeros(self):
        url = reverse('usuario:crear')
        data = {
            'nombre': 'Nuevo',
            'apellido': 'Usuario',
            'email': 'nuevo@test.com',
            'telefono': '987654',
            'direccion': 'Direccion',
            'ci': '123456789',
            'usuario': 'new_user_no_numbers',
            'password': 'OnlyLettersPassword',  # Solo letras
            'rol': self.rol_admin.id_rol
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Usuario.objects.filter(usuario='new_user_no_numbers').exists())

    def test_editar_usuario_sin_cambiar_password(self):
        # Crear usuario para editar
        user_to_edit = Usuario.objects.create(
            nombre="Edit",
            apellido="Me",
            email="edit@me.com",
            telefono="654321",
            direccion="Edit Dir",
            ci="999999",
            usuario="edit_me",
            password="originalpasswordhash",
            rol=self.rol_admin,
            estado=True
        )
        url = reverse('usuario:editar', args=[user_to_edit.id_usuario])
        data = {
            'nombre': 'Editado',
            'apellido': 'Me',
            'email': 'edit@me.com',
            'telefono': '654321',
            'direccion': 'Edit Dir',
            'ci': '999999',
            'usuario': 'edit_me_updated',
            'password': '',  # Vacío para no cambiar
            'rol': self.rol_admin.id_rol
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        
        # Cargar de DB y verificar
        updated_user = Usuario.objects.get(id_usuario=user_to_edit.id_usuario)
        self.assertEqual(updated_user.usuario, 'edit_me_updated')
        # La contraseña no debe haber cambiado ni re-hashearse
        self.assertEqual(updated_user.password, 'originalpasswordhash')


class WebSecurityGeneralTests(TestCase):
    def setUp(self):
        # Crear roles
        self.rol_admin, _ = Rol.objects.get_or_create(nombre="Administrador")
        self.rol_vendedor, _ = Rol.objects.get_or_create(nombre="Vendedor")

        # Hashear contraseñas correctas para pruebas
        from django.contrib.auth.hashers import make_password
        self.password_plana = "AdminPass123"
        self.admin_user = Usuario.objects.create(
            nombre="Admin",
            apellido="Seguridad",
            email="admin_seg@test.com",
            telefono="1111",
            direccion="Admin Office",
            ci="11112222",
            usuario="admin_seg",
            password=make_password(self.password_plana),
            rol=self.rol_admin,
            estado=True
        )

        self.vendedor_user = Usuario.objects.create(
            nombre="Vendedor",
            apellido="Seguridad",
            email="vendedor_seg@test.com",
            telefono="2222",
            direccion="Storefront",
            ci="33334444",
            usuario="vendedor_seg",
            password=make_password("VendPass123"),
            rol=self.rol_vendedor,
            estado=True
        )

        # Configurar Clientes y Proveedores para compras/ventas
        self.cliente = Cliente.objects.create(
            nombre="Cliente",
            apellido="Prueba",
            email="cliente@prueba.com",
            telefono="7777777",
            direccion="Direccion",
            ci="1234567",
            estado=True
        )
        self.proveedor = Proveedor.objects.create(
            nombre="Proveedor",
            telefono="6666666",
            estado=True
        )

        # Categoria y Marca
        self.categoria = Categoria.objects.create(nombre="Tecnologia", estado=True)
        self.marca = Marca.objects.create(nombre="Sismeing", estado=True)

        # Tipo de cambio
        self.tipo_cambio = TipoCambio.objects.create(valor=Decimal("6.96"), fecha=timezone.now().date(), estado=True)

        # Producto
        self.producto = Producto.objects.create(
            nombre="Lapicero",
            descripcion="Lapicero de prueba",
            precio_usd=Decimal("2.00"),
            precio_actual=Decimal("13.92"),
            stock=100,
            categoria=self.categoria,
            marca=self.marca,
            estado=True
        )

        self.client = Client()
        self.patcher_ai = patch('apps.producto.views.generar_especificaciones_producto_async')
        self.mock_ai = self.patcher_ai.start()

    def tearDown(self):
        self.patcher_ai.stop()

    def login_as(self, usuario):
        session = self.client.session
        session['usuario_id'] = str(usuario.id_usuario)
        session['usuario_nombre'] = f"{usuario.nombre} {usuario.apellido}"
        session['usuario_rol'] = str(usuario.rol)
        session.save()

    def test_login_brute_force_lockout(self):
        url = reverse('usuario:login')
        
        # Simular 5 intentos fallidos
        for _ in range(5):
            response = self.client.post(url, {
                'usuario': 'admin_seg',
                'password': 'WrongPassword'
            })
            self.assertContains(response, 'Usuario o contraseña incorrectos.')

        # Verificar que el registro de intento existe y está bloqueado
        intento = IntentoLogin.objects.get(usuario_ingresado='admin_seg')
        self.assertEqual(intento.cantidad_intentos, 5)
        self.assertIsNotNone(intento.bloqueado_hasta)

        # El 6º intento fallido debe estar bloqueado temporalmente
        response = self.client.post(url, {
            'usuario': 'admin_seg',
            'password': 'WrongPassword'
        })
        self.assertContains(response, 'Se realizaron varios intentos de inicio de sesión')

        # Si el usuario intenta con la contraseña CORRECTA mientras está bloqueado, sigue denegado
        response = self.client.post(url, {
            'usuario': 'admin_seg',
            'password': self.password_plana
        })
        self.assertContains(response, 'Se realizaron varios intentos de inicio de sesión')

    def test_login_generic_error_messages(self):
        url = reverse('usuario:login')
        
        # Caso 1: Contraseña incorrecta para usuario existente
        response = self.client.post(url, {
            'usuario': 'admin_seg',
            'password': 'WrongPassword'
        })
        self.assertContains(response, 'Usuario o contraseña incorrectos.')
        self.assertNotContains(response, 'Contraseña incorrecta')

        # Caso 2: Usuario inexistente
        response = self.client.post(url, {
            'usuario': 'usuario_fantasma',
            'password': 'SomePassword'
        })
        self.assertContains(response, 'Usuario o contraseña incorrectos.')
        self.assertNotContains(response, 'El usuario no existe')

    def test_role_based_access_control(self):
        # 1. Sin autenticar
        url_usuarios = reverse('usuario:index')
        response = self.client.get(url_usuarios)
        # Redirección al login
        self.assertRedirects(response, reverse('usuario:login'))

        # 2. Vendedor intentando acceder a usuarios
        self.login_as(self.vendedor_user)
        response = self.client.get(url_usuarios)
        self.assertEqual(response.status_code, 403) # Acceso denegado

        # 3. Administrador intentando acceder
        self.login_as(self.admin_user)
        response = self.client.get(url_usuarios)
        self.assertEqual(response.status_code, 200)

    def test_session_user_deactivation_real_time(self):
        self.login_as(self.admin_user)
        
        # Desactivar usuario en base de datos
        self.admin_user.estado = False
        self.admin_user.save()

        # Siguiente petición a ruta protegida debe denegar acceso y redirigir
        url_usuarios = reverse('usuario:index')
        response = self.client.get(url_usuarios)
        self.assertRedirects(response, reverse('usuario:login'))

    def test_session_user_role_change_real_time(self):
        self.login_as(self.admin_user)

        # Cambiar rol de Administrador a Vendedor en base de datos
        self.admin_user.rol = self.rol_vendedor
        self.admin_user.save()

        # Siguiente petición a ruta administrativa debe ser bloqueada con 403
        url_usuarios = reverse('usuario:index')
        response = self.client.get(url_usuarios)
        self.assertEqual(response.status_code, 403)

    def test_csrf_protection_enforcement(self):
        # Crear un cliente con validación CSRF obligatoria
        client_csrf = Client(enforce_csrf_checks=True)
        # Simular login en sesión
        session = client_csrf.session
        session['usuario_id'] = str(self.admin_user.id_usuario)
        session['usuario_nombre'] = "Admin"
        session['usuario_rol'] = "Administrador"
        session.save()

        # Intentar POST sin token csrf
        url = reverse('usuario:crear')
        response = client_csrf.post(url, {
            'nombre': 'Prueba',
            'apellido': 'CSRF',
            'email': 'csrf@test.com',
            'telefono': '0000',
            'direccion': 'N/A',
            'ci': '000000',
            'usuario': 'test_csrf_user',
            'password': 'SecurePassword123',
            'rol': self.rol_admin.id_rol
        })
        self.assertEqual(response.status_code, 403) # Forbidden por falta de CSRF

    def test_data_validation_negative_values(self):
        self.login_as(self.admin_user)

        # 1. Intentar registrar venta con cantidad negativa
        url_venta = reverse('venta:crear')
        data_venta = {
            'cliente': self.cliente.id_cliente,
            'fecha': '2026-07-13',
            'producto[]': [self.producto.id_producto],
            'cantidad[]': [-5], # Negativo
            'precio[]': [13.92],
            'descuento[]': [0.00]
        }
        response = self.client.post(url_venta, data_venta)
        # La venta no debe registrarse y debe retornar redirect con mensaje de error
        self.assertRedirects(response, reverse('venta:index'))
        self.assertFalse(Venta.objects.filter(cliente=self.cliente).exists())

        # 2. Intentar registrar compra con cantidad o precio negativo
        url_compra = reverse('compra:crear')
        data_compra = {
            'proveedor_id': self.proveedor.id_proveedor,
            'fecha': '2026-07-13',
            'producto[]': [self.producto.id_producto],
            'cantidad[]': [10],
            'precio[]': [-2.00], # Precio compra negativo
            'precio_venta[]': [15.00]
        }
        response = self.client.post(url_compra, data_compra)
        self.assertRedirects(response, reverse('compra:index'))
        self.assertFalse(Compra.objects.filter(proveedor=self.proveedor).exists())

    def test_venta_atomic_transaction_rollback(self):
        self.login_as(self.admin_user)
        url_venta = reverse('venta:crear')
        
        # Cantidad de ventas iniciales
        ventas_iniciales = Venta.objects.count()

        # Simular error en consumir_lotes_peps para disparar rollback
        with patch('apps.venta.views.consumir_lotes_peps', side_effect=Exception("Simulated PEPS Failure")):
            data_venta = {
                'cliente': self.cliente.id_cliente,
                'fecha': '2026-07-13',
                'producto[]': [self.producto.id_producto],
                'cantidad[]': [5],
                'precio[]': [13.92],
                'descuento[]': [0.00]
            }
            response = self.client.post(url_venta, data_venta)
            
        # Verificar que NO se haya insertado la venta (rollback exitoso)
        self.assertEqual(Venta.objects.count(), ventas_iniciales)

    def test_image_upload_validation(self):
        self.login_as(self.admin_user)
        url_crear = reverse('producto:crear')

        # 1. Extensión maliciosa (.exe)
        file_exe = SimpleUploadedFile("malicious.exe", b"MZ\x90\x00\x03\x00\x00\x00", content_type="application/x-msdownload")
        response = self.client.post(url_crear, {
            'nombre': 'Producto Exe',
            'descripcion': 'Falso',
            'categoria': self.categoria.id_categoria,
            'marca': self.marca.id_marca,
            'imagen': file_exe
        })
        self.assertRedirects(response, reverse('producto:index'))
        self.assertFalse(Producto.objects.filter(nombre='Producto Exe').exists())

        # 2. Imagen falsa/corrupta (contenido que no es imagen real)
        file_fake = SimpleUploadedFile("fake.png", b"Fake content here not image", content_type="image/png")
        response = self.client.post(url_crear, {
            'nombre': 'Producto Fake',
            'descripcion': 'Falso',
            'categoria': self.categoria.id_categoria,
            'marca': self.marca.id_marca,
            'imagen': file_fake
        })
        self.assertRedirects(response, reverse('producto:index'))
        self.assertFalse(Producto.objects.filter(nombre='Producto Fake').exists())

        # 3. Imagen válida -> Renombrado seguro a UUID y conversión a webp
        import io
        img_buffer = io.BytesIO()
        img = Image.new('RGB', (100, 100), color='red')
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        file_valid = SimpleUploadedFile("valid.png", img_buffer.read(), content_type="image/png")
        response = self.client.post(url_crear, {
            'nombre': 'Producto Valido',
            'descripcion': 'Valido',
            'categoria': self.categoria.id_categoria,
            'marca': self.marca.id_marca,
            'imagen': file_valid
        })
        self.assertRedirects(response, reverse('producto:index'))
        
        prod = Producto.objects.get(nombre='Producto Valido')
        self.assertTrue(prod.imagen)
        # Debe guardarse con la extensión .webp y contener "producto_" y un identificador aleatorio
        self.assertTrue(prod.imagen.name.endswith('.webp'))
        self.assertTrue("producto_" in prod.imagen.name)

    def test_http_security_headers_and_cookies(self):
        url = reverse('usuario:login')
        response = self.client.get(url)

        # 1. Cabeceras HTTP
        self.assertEqual(response.headers.get('X-Frame-Options'), 'DENY')
        self.assertEqual(response.headers.get('X-Content-Type-Options'), 'nosniff')
        self.assertEqual(response.headers.get('Referrer-Policy'), 'same-origin')

        # 2. Cookies de Sesión
        # Generar una sesión para tener la cookie de sesión disponible
        self.login_as(self.admin_user)
        response = self.client.get(reverse('web:dashboard'))
        session_cookie = self.client.cookies.get('sessionid')
        self.assertIsNotNone(session_cookie)
        self.assertTrue(session_cookie.get('httponly'))
        self.assertEqual(session_cookie.get('samesite'), 'Lax')

