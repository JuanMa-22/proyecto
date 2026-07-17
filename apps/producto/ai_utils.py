import threading
import json
import re
from groq import Groq
from django.db import close_old_connections
from apps.productoEspecificacion.models import ProductoEspecificacion
from apps.producto.models import Producto

INSTRUCCIONES_IA_EXTRACCION = """Eres un experto en hardware y componentes de computadora.
El usuario te dará el nombre de un producto tecnológico (junto con su marca y categoría).
Tu único trabajo es devolver un OBJETO JSON con sus especificaciones técnicas.
IMPORTANTE:
- Si no encuentras el dato, usa null
- No inventes datos extremos, usa conocimiento general
- Solo llena lo que se pueda inferir del producto
- DEBES devolver SOLO el JSON, sin texto antes ni después.

FORMATO OBLIGATORIO:
{
  "producto_especificacion": {
    "socket": "",
    "chipset": "",
    "tipo_ram": "",
    "vram": "",
    "watts": "",
    "velocidad_ram": "",
    "almacenamiento": "",
    "pci": ""
  }
}"""

def _trabajador_generar_especificaciones(id_producto, nombre_producto, nombre_marca, nombre_categoria):
    """
    Esta función se ejecuta de fondo. Se conecta a la IA y guarda las especificaciones en la base de datos.
    """
    close_old_connections()
    try:
        from decouple import config
        llave_api = config('GROQ_API_KEY', default="")
        if not llave_api:
            # Si la clave API no está configurada, crear especificación vacía para evitar que el proceso falle silenciosamente
            try:
                producto_db = Producto.objects.get(id_producto=id_producto)
                ProductoEspecificacion.objects.update_or_create(producto=producto_db)
            except Exception as e:
                print(f"Error al crear especificación vacía para el producto {id_producto}: {e}")
            return  # Salir del hilo después de crear la especificación vacía
            
        print('Iniciando llamada a Groq API...')
        try:
            cliente_ia = Groq(api_key=llave_api)
            texto_enviado = f"Producto: {nombre_producto} | Marca: {nombre_marca} | Categoría: {nombre_categoria}"
            
            # Pedimos a la IA que nos dé el JSON
            respuesta = cliente_ia.chat.completions.create(
                messages=[
                    {"role": "system", "content": INSTRUCCIONES_IA_EXTRACCION},
                    {"role": "user", "content": texto_enviado}
                ],
                model="llama-3.1-8b-instant",
                temperature=0.2, # Muy bajo para evitar alucinaciones
            )
            texto_respuesta = respuesta.choices[0].message.content
            print('Respuesta recibida de Groq')
        except Exception as api_err:
            print(f'Error al llamar a Groq API: {api_err}')
            raise
        
        # Intentar extraer JSON directamente; si falla, buscar cualquier objeto JSON en el texto
        try:
            datos = json.loads(texto_respuesta)
        except json.JSONDecodeError:
            # Buscar el primer bloque JSON en la respuesta
            encontrar_json = re.search(r'\{[\s\S]*\}', texto_respuesta)
            if encontrar_json:
                try:
                    datos = json.loads(encontrar_json.group())
                except json.JSONDecodeError:
                    datos = {}
            else:
                datos = {}
        
        # Intentar obtener el bloque de especificaciones
        especificaciones = datos.get("producto_especificacion")
        if especificaciones is None:
            # Si la IA devolvió un objeto con el nombre del producto como clave, usar ese valor
            if isinstance(datos, dict) and len(datos) == 1:
                especificaciones = next(iter(datos.values()))
            else:
                especificaciones = {}
        
        # Debug: imprimir la respuesta completa de la IA y los datos extraídos
        print(f'Procesando producto {id_producto}: Respuesta IA raw: {texto_respuesta}')
        print(f'Datos extraídos: {especificaciones}')
        
        # Guardar o actualizar especificación en la base de datos
        producto_db = Producto.objects.get(id_producto=id_producto)
        defaults = {
            'socket': especificaciones.get('socket'),
            'chipset': especificaciones.get('chipset'),
            'tipo_ram': especificaciones.get('tipo_ram'),
            'vram': especificaciones.get('vram'),
            'watts': str(especificaciones.get('watts')) if especificaciones.get('watts') is not None else None,
            'velocidad_ram': especificaciones.get('velocidad_ram'),
            'almacenamiento': especificaciones.get('almacenamiento'),
            'pci': especificaciones.get('pci'),
        }
        # update_or_create actualiza si ya existe la fila para ese producto
        ProductoEspecificacion.objects.update_or_create(producto=producto_db, defaults=defaults)

    except Exception as error:
        print(f"Ocurrió un error al generar especificaciones para el producto {id_producto}: {str(error)}")
        # Intentar crear especificación vacía para evitar ausencia de registro
        try:
            producto_db = Producto.objects.get(id_producto=id_producto)
            ProductoEspecificacion.objects.get_or_create(producto=producto_db)
        except Exception as e:
            print(f"Error al crear especificación vacía en el manejo de excepción: {e}")
    finally:
        close_old_connections()

def generar_especificaciones_producto_async(id_producto, nombre_producto, nombre_marca, nombre_categoria):
    """
    Inicia un hilo (Thread) secundario de forma asíncrona. 
    Esto evita que la página se quede cargando o se congele mientras la IA piensa.
    """
    hilo = threading.Thread(
        target=_trabajador_generar_especificaciones,
        args=(id_producto, nombre_producto, nombre_marca, nombre_categoria)
    )
    hilo.start()
