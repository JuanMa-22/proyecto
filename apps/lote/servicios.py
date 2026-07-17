"""
servicios.py — Lógica del método PEPS (Primero en Entrar, Primero en Salir) / FIFO para la gestión de lotes.

Este archivo contiene los servicios necesarios para:
1. Consumir unidades de los lotes existentes aplicando PEPS.
2. Crear un lote nuevo cuando se registra una compra.
3. Inicializar y asociar proveedores a lotes para productos con stock preexistente.
"""

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from .models import LoteProducto, LoteConsumo


def consumir_lotes_peps(producto, detalle_venta, cantidad):
    """
    Descuenta la cantidad de unidades vendidas utilizando la lógica PEPS/FIFO:
    descuenta del lote activo más antiguo (por fecha de entrada) que tenga existencias.
    """

    if cantidad <= 0:
        raise ValueError("La cantidad a consumir debe ser mayor a cero.")

    consumos_creados = []

    with transaction.atomic():
        # Obtener los lotes activos con existencias, ordenados por fecha de entrada (los más antiguos primero)
        lotes = (
            LoteProducto.objects
            .select_for_update()
            .filter(
                producto=producto,
                cantidad_disponible__gt=0,
                estado=True
            )
            .order_by("fecha_entrada", "id_lote")
        )

        # Calcular el stock total disponible en todos los lotes
        total_disponible = (
            lotes.aggregate(total=Sum("cantidad_disponible"))["total"] or 0
        )

        # Validar si hay suficiente stock disponible antes de realizar el descuento
        if total_disponible < cantidad:
            raise ValueError(
                f"Stock insuficiente en lotes PEPS. "
                f"Disponible: {total_disponible}, Solicitado: {cantidad}."
            )

        restante = cantidad

        # Iterar sobre los lotes para consumir el stock requerido
        for lote in lotes:
            if restante <= 0:
                break

            # Determinar la cantidad a consumir de este lote específico
            consumo = min(lote.cantidad_disponible, restante)

            # Descontar del lote
            lote.cantidad_disponible -= consumo

            # Si el lote se queda sin existencias, se desactiva
            if lote.cantidad_disponible == 0:
                lote.estado = False
                lote.save(update_fields=["cantidad_disponible", "estado", "updated_at"])
            else:
                lote.save(update_fields=["cantidad_disponible", "updated_at"])

            # Registrar el consumo del lote para mantener la trazabilidad
            registro = LoteConsumo.objects.create(
                lote=lote,
                detalle_venta=detalle_venta,
                cantidad=consumo,
            )

            consumos_creados.append(registro)
            restante -= consumo

        # Sincronizar el stock total de la tabla Producto con el stock real disponible en lotes
        nuevo_stock = (
            LoteProducto.objects
            .filter(producto=producto, cantidad_disponible__gt=0)
            .aggregate(total=Sum("cantidad_disponible"))["total"] or 0
        )

        producto.stock = nuevo_stock
        producto.save(update_fields=["stock"])

    return consumos_creados


def crear_lote_desde_compra(compra, detalle_compra, producto, cantidad, precio_usd):
    """
    Crea un nuevo lote de producto asociado a una compra y actualiza el stock del producto.
    """

    if cantidad <= 0:
        raise ValueError("La cantidad del lote comprado debe ser mayor a cero.")

    with transaction.atomic():
        # Crear el registro del lote con los datos de la compra
        lote = LoteProducto.objects.create(
            producto=producto,
            detalle_compra=detalle_compra,
            proveedor=compra.proveedor,
            fecha_entrada=compra.fecha,
            cantidad_inicial=cantidad,
            cantidad_disponible=cantidad,
            precio_costo_usd=precio_usd,
            estado=True,
        )

        # Sincronizar el stock total del producto
        nuevo_stock = (
            LoteProducto.objects
            .filter(producto=producto, cantidad_disponible__gt=0)
            .aggregate(total=Sum("cantidad_disponible"))["total"] or 0
        )

        producto.stock = nuevo_stock
        producto.save(update_fields=["stock"])

    return lote


def inicializar_lotes_existentes():
    """
    Genera un lote inicial para los productos con stock actual mayor a cero
    que aún no tengan lotes registrados. Intenta asociar el proveedor y la fecha
    de la última compra registrada para mantener consistencia.
    """
    from apps.producto.models import Producto
    from apps.detalleCompra.models import DetalleCompra

    creados = 0
    actualizados = 0

    with transaction.atomic():
        productos = Producto.objects.select_for_update().filter(
            stock__gt=0,
            estado=True
        )

        for producto in productos:
            # Buscar la última compra registrada de este producto
            ultimo_detalle = (
                DetalleCompra.objects
                .filter(producto=producto)
                .select_related('compra__proveedor')
                .order_by('-compra__fecha', '-created_at')
                .first()
            )

            # Extraer referencias de proveedor, detalle y fecha de compra
            proveedor_ref   = ultimo_detalle.compra.proveedor if ultimo_detalle else None
            detalle_ref     = ultimo_detalle if ultimo_detalle else None
            fecha_ref       = ultimo_detalle.compra.fecha if ultimo_detalle else timezone.localdate()

            lote_existente = LoteProducto.objects.filter(producto=producto).first()

            if not lote_existente:
                # Crear el lote inicial con los datos encontrados
                LoteProducto.objects.create(
                    producto=producto,
                    detalle_compra=detalle_ref,
                    proveedor=proveedor_ref,
                    fecha_entrada=fecha_ref,
                    cantidad_inicial=producto.stock,
                    cantidad_disponible=producto.stock,
                    precio_costo_usd=producto.precio_usd,
                    estado=True,
                )
                creados += 1

            elif lote_existente.proveedor is None and proveedor_ref:
                # Actualizar el lote inicial con la información de proveedor y fecha de compra encontrada
                lote_existente.proveedor      = proveedor_ref
                lote_existente.detalle_compra = detalle_ref
                lote_existente.fecha_entrada  = fecha_ref
                lote_existente.save(update_fields=['proveedor', 'detalle_compra', 'fecha_entrada', 'updated_at'])
                actualizados += 1

    return creados, actualizados
