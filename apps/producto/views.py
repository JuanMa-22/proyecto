from django.shortcuts import render, redirect
from django.http import JsonResponse
from decimal import Decimal
from .models import Producto
from apps.productoEspecificacion.models import ProductoEspecificacion
from apps.categoria.models import Categoria
from apps.marca.models import Marca
from apps.historialPrecio.models import HistorialPrecio
from apps.productoEspecificacion.models import ProductoEspecificacion
from django.utils import timezone
from apps.tipoCambio.models import TipoCambio
from apps.usuario.decorators import login_requerido, solo_admin
from django.contrib import messages
from .ai_utils import generar_especificaciones_producto_async, _trabajador_generar_especificaciones
from django.urls import reverse
from apps.web.reportes_generator import generar_pdf_reporte, generar_excel_reporte

# Create your views here.
@login_requerido
def index(request):
    inactivos = request.GET.get('inactivos') == 'true'
    if inactivos:
        productos = Producto.objects.select_related('categoria', 'marca').filter(estado=False)
    else:
        productos = Producto.objects.select_related('categoria', 'marca').filter(estado=True)
        
    categorias = Categoria.objects.all()
    marcas = Marca.objects.all()

    # Filtros por categoría y/o marca via GET
    categoria_sel = request.GET.get('categoria', '')
    marca_sel = request.GET.get('marca', '')

    if categoria_sel:
        productos = productos.filter(categoria__id_categoria=categoria_sel)
    if marca_sel:
        productos = productos.filter(marca__id_marca=marca_sel)

    return render(request, 'producto/index.html', {
        'productos': productos,
        'categorias': categorias,
        'marcas': marcas,
        'categoria_sel': categoria_sel,
        'marca_sel': marca_sel,
        'mostrar_inactivos': inactivos,
    })

from PIL import Image
import io
import uuid
import os
from django.core.files.base import ContentFile

def procesar_y_validar_imagen_subida(archivo):
    """
    Valida la extensión, el tamaño (máximo 5MB) y que el contenido del archivo
    sea realmente una imagen válida utilizando Pillow.
    Normaliza a formato WEBP con un nombre seguro aleatorio (UUID).
    """
    if not archivo:
        return None
    ext = os.path.splitext(archivo.name)[1].lower()
    if ext not in ['.png', '.jpg', '.jpeg', '.webp']:
        raise ValueError("Formato de imagen no permitido. Solo se aceptan PNG, JPG, JPEG y WEBP.")
    
    max_size = 5 * 1024 * 1024  # 5 MB
    if archivo.size > max_size:
        raise ValueError("La imagen excede el límite de tamaño permitido de 5 MB.")
        
    try:
        img = Image.open(archivo)
        img.verify()
    except Exception:
        raise ValueError("El archivo no es una imagen válida o está corrupto.")
        
    try:
        archivo.seek(0)
        img = Image.open(archivo)
        
        output_buffer = io.BytesIO()
        img.save(output_buffer, format='WEBP', quality=85)
        output_buffer.seek(0)
        
        nuevo_nombre = f"producto_{uuid.uuid4().hex}.webp"
        return ContentFile(output_buffer.read(), name=nuevo_nombre)
    except Exception as e:
        raise ValueError(f"Error procesando la imagen: {str(e)}")

@solo_admin
def crearProducto(request):
    categorias = Categoria.objects.all()
    marcas = Marca.objects.all()

    if request.method == 'POST':
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('is_ajax') == 'true'
        nombre = request.POST['nombre'].strip()
        
        if Producto.objects.filter(nombre__iexact=nombre).exists():
            msg = f"El producto '{nombre}' ya existe."
            if is_ajax:
                return JsonResponse({'success': False, 'message': msg}, status=400)
            messages.error(request, msg)
            return redirect('producto:index')

        categoria = Categoria.objects.get(id_categoria=request.POST['categoria'])
        marca = Marca.objects.get(id_marca=request.POST['marca'])

        imagen_subida = request.FILES.get('imagen')
        imagen_procesada = None
        if imagen_subida:
            try:
                imagen_procesada = procesar_y_validar_imagen_subida(imagen_subida)
            except Exception as e:
                msg = str(e)
                if is_ajax:
                    return JsonResponse({'success': False, 'message': msg}, status=400)
                messages.error(request, msg)
                return redirect('producto:index')

        producto = Producto.objects.create(
            nombre=nombre,
            descripcion=request.POST['descripcion'],
            precio_actual=0.00,
            precio_usd=0.00,
            stock=0,
            categoria=categoria,
            marca=marca,
            imagen=imagen_procesada,
            estado=True
        )
        # Garantizar que exista una especificación (vacía) al crear el producto
        ProductoEspecificacion.objects.get_or_create(producto=producto)

        # Disparar la recolección de especificaciones por IA en segundo plano
        generar_especificaciones_producto_async(
            producto.id_producto,
            producto.nombre,
            marca.nombre,
            categoria.nombre
        )

        msg = "Producto creado exitosamente."
        if is_ajax:
            return JsonResponse({'success': True, 'id': str(producto.id_producto), 'nombre': producto.nombre, 'message': msg})

        messages.success(request, msg)
        return redirect('producto:index')

    return render(request, 'producto/crear.html', {
        'categorias': categorias,
        'marcas': marcas,
    })

@solo_admin
def editarProducto(request, id_producto):
    producto = Producto.objects.get(id_producto=id_producto)
    categorias = Categoria.objects.all()
    marcas = Marca.objects.all()

    if request.method == 'POST':
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
        nombre = request.POST['nombre'].strip()
        if Producto.objects.filter(nombre__iexact=nombre).exclude(id_producto=id_producto).exists():
            msg = f"Ya existe otro producto con el nombre '{nombre}'."
            if is_ajax:
                return JsonResponse({'success': False, 'message': msg}, status=400)
            messages.error(request, msg)
            return redirect('producto:index')

        nuevo_precio_usd = Decimal(request.POST['precio'])
        
        # Obtener el último tipo de cambio activo
        tipo_cambio = TipoCambio.objects.filter(estado=True).order_by('-fecha', '-created_at').first()

        producto.nombre = nombre
        producto.descripcion = request.POST['descripcion']
        producto.categoria = Categoria.objects.get(id_categoria=request.POST['categoria'])
        producto.marca = Marca.objects.get(id_marca=request.POST['marca'])
        
        if request.FILES.get('imagen'):
            try:
                producto.imagen = procesar_y_validar_imagen_subida(request.FILES.get('imagen'))
            except Exception as e:
                msg = str(e)
                if is_ajax:
                    return JsonResponse({'success': False, 'message': msg}, status=400)
                messages.error(request, msg)
                return redirect('producto:index')

        # Si el precio en USD cambió o queremos forzar actualización con nuevo TC
        if producto.precio_usd != nuevo_precio_usd:
            HistorialPrecio.objects.filter(
                producto=producto,
                estado=True
            ).update(
                estado=False,
                fecha_fin=timezone.now()
            )

            if tipo_cambio:
                HistorialPrecio.objects.create(
                    producto=producto,
                    tipo_cambio=tipo_cambio,
                    precio_compra=nuevo_precio_usd,
                    precio_venta=nuevo_precio_usd * tipo_cambio.valor,
                    fecha_inicio=timezone.now()
                )

            producto.precio_usd = nuevo_precio_usd

        # Recalcular precio actual siempre con el último TC disponible
        if tipo_cambio:
            producto.precio_actual = producto.precio_usd * tipo_cambio.valor
        else:
            producto.precio_actual = producto.precio_usd

        producto.estado = True
        producto.save()
        msg = "Producto actualizado exitosamente."
        if is_ajax:
            return JsonResponse({'success': True, 'message': msg})
        messages.success(request, msg)
        return redirect('producto:index')

    return render(request, 'producto/editar.html', {
        'producto': producto,
        'categorias': categorias,
        'marcas': marcas,
    })


@solo_admin
def eliminarProducto(request, id_producto):
    producto = Producto.objects.get(id_producto=id_producto)
    producto.estado = False
    producto.save()
    messages.success(request, "Producto desactivado exitosamente.")
    return redirect('producto:index')


@solo_admin
def activarProducto(request, id_producto):
    producto = Producto.objects.get(id_producto=id_producto)
    producto.estado = True
    producto.save()
    messages.success(request, "Producto reactivado exitosamente.")
    return redirect(f"{reverse('producto:index')}?inactivos=true")


@login_requerido
def especificacionesProducto(request, id_producto):
    """Devuelve las especificaciones técnicas de un producto en formato JSON."""
    producto = Producto.objects.get(id_producto=id_producto)
    espec = ProductoEspecificacion.objects.filter(producto=producto).first()

    datos = {
        'nombre': producto.nombre,
        'socket': espec.socket if espec else None,
        'chipset': espec.chipset if espec else None,
        'tipo_ram': espec.tipo_ram if espec else None,
        'vram': espec.vram if espec else None,
        'watts': espec.watts if espec else None,
        'velocidad_ram': espec.velocidad_ram if espec else None,
        'almacenamiento': espec.almacenamiento if espec else None,
        'pci': espec.pci if espec else None,
    }
    return JsonResponse(datos)


@login_requerido
def reporte_productos_pdf(request):
    productos = Producto.objects.select_related('categoria', 'marca').all().order_by('nombre')
    
    # Filtros por categoría y/o marca via GET
    categoria_sel = request.GET.get('categoria', '')
    marca_sel = request.GET.get('marca', '')

    if categoria_sel:
        productos = productos.filter(categoria__id_categoria=categoria_sel)
    if marca_sel:
        productos = productos.filter(marca__id_marca=marca_sel)

    headers = ['Nombre', 'Descripción', 'Categoría', 'Marca', 'Stock', 'Precio (USD)', 'Precio (Bs)', 'Estado']
    data = []
    for p in productos:
        estado_str = "Activo" if p.estado else "Inactivo"
        desc = p.descripcion if p.descripcion else ""
        data.append([
            p.nombre,
            desc,
            p.categoria.nombre,
            p.marca.nombre,
            p.stock,
            float(p.precio_usd),
            float(p.precio_actual),
            estado_str
        ])
    return generar_pdf_reporte("Reporte de Productos", headers, data, "reporte_productos.pdf")


@login_requerido
def reporte_productos_excel(request):
    productos = Producto.objects.select_related('categoria', 'marca').all().order_by('nombre')
    
    # Filtros por categoría y/o marca via GET
    categoria_sel = request.GET.get('categoria', '')
    marca_sel = request.GET.get('marca', '')

    if categoria_sel:
        productos = productos.filter(categoria__id_categoria=categoria_sel)
    if marca_sel:
        productos = productos.filter(marca__id_marca=marca_sel)

    headers = ['Nombre', 'Descripción', 'Categoría', 'Marca', 'Stock', 'Precio (USD)', 'Precio (Bs)', 'Estado']
    data = []
    for p in productos:
        estado_str = "Activo" if p.estado else "Inactivo"
        desc = p.descripcion if p.descripcion else ""
        data.append([
            p.nombre,
            desc,
            p.categoria.nombre,
            p.marca.nombre,
            p.stock,
            float(p.precio_usd),
            float(p.precio_actual),
            estado_str
        ])
    return generar_excel_reporte("Reporte de Productos", headers, data, "reporte_productos.xlsx")