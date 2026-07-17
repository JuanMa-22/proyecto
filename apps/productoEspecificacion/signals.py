from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Producto

from apps.especificacion.models import ProductoEspecificacion
from apps.especificacion.ia import generar_especificaciones


@receiver(post_save, sender=Producto)
def crear_especificacion(sender, instance, created, **kwargs):

    if created:

        data = generar_especificaciones(instance.nombre)

        ProductoEspecificacion.objects.create(
            producto=instance,
            socket=data.get("socket"),
            chipset=data.get("chipset"),
            tipo_ram=data.get("tipo_ram"),
            vram=data.get("vram"),
            watts=data.get("watts"),
            almacenamiento=data.get("almacenamiento"),
            velocidad_ram=data.get("velocidad_ram")
        )