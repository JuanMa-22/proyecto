from django.db.models.signals import post_migrate
from django.dispatch import receiver
from decouple import config
from django.contrib.auth.hashers import make_password, check_password

from .models import Usuario, Rol

@receiver(post_migrate)
def crear_datos(sender, **kwargs):

    rol_admin = Rol.objects.filter(nombre="Administrador").first()
    if not rol_admin:
        rol_admin = Rol.objects.create(nombre="Administrador")

    rol_vendedor = Rol.objects.filter(nombre="Vendedor").first()
    if not rol_vendedor:
        rol_vendedor = Rol.objects.create(nombre="Vendedor")

    usuario_admin = Usuario.objects.filter(
        usuario=config('ADMIN_USUARIO')
    ).first()

    if not usuario_admin:
        Usuario.objects.create(
            nombre="Juan",
            apellido="Apaza",
            email="juan@gmail.com",
            telefono="77777777",
            direccion="La Paz",
            ci="12345678",
            usuario=config('ADMIN_USUARIO'),
            password=make_password(config('ADMIN_PASSWORD')),
            rol=rol_admin,
            estado=True
        )
        print("Administrador creado")
    else:
        if not check_password(config('ADMIN_PASSWORD'), usuario_admin.password):
            usuario_admin.password = make_password(config('ADMIN_PASSWORD'))
            usuario_admin.save()
            print("Contraseña del administrador actualizada")