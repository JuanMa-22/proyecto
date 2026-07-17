import ollama
import json

def generar_especificaciones(nombre_producto):

    prompt = f"""
    Eres un experto en hardware.

    Devuelve SOLO JSON válido.

    Genera las especificaciones técnicas del producto:

    {nombre_producto}

    Campos:
    - socket
    - chipset
    - tipo_ram
    - vram
    - watts
    - almacenamiento
    - velocidad_ram

    Si algún campo no aplica devuelve null.
    """

    response = ollama.chat(
        model='llama-3.1-8b-instant',
        messages=[
            {
                'role': 'user',
                'content': prompt
            }
        ]
    )

    contenido = response['message']['content']

    return json.loads(contenido)        