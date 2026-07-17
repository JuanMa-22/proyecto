import asyncio
import re
import logging
from io import BytesIO
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.clickjacking import xframe_options_exempt

logger = logging.getLogger(__name__)

# Voz en español latinoamericano (Microsoft Edge TTS)
VOZ_TTS = "es-MX-DaliaNeural"


def limpiar_texto_para_tts(texto: str) -> str:
    """
    Limpia el texto de Markdown y símbolos especiales antes de enviarlo al TTS,
    para que la voz suene natural y no lea asteriscos, almohadillas, etc.
    """
    # Eliminar bloques de código
    texto = re.sub(r'```[\s\S]*?```', '', texto)
    # Eliminar negritas y cursivas (**texto**, *texto*, __texto__)
    texto = re.sub(r'\*{1,3}([^*]+)\*{1,3}', r'\1', texto)
    texto = re.sub(r'_{1,3}([^_]+)_{1,3}', r'\1', texto)
    # Eliminar encabezados Markdown (##, ###, etc.)
    texto = re.sub(r'^#{1,6}\s+', '', texto, flags=re.MULTILINE)
    # Eliminar filas de tabla con guiones (|---|---|)
    texto = re.sub(r'^\|[\s\-:|]+\|$', '', texto, flags=re.MULTILINE)
    # Eliminar barras verticales de tablas
    texto = re.sub(r'\|', ' ', texto)
    # Eliminar viñetas de listas (- item, * item)
    texto = re.sub(r'^[\-\*]\s+', '', texto, flags=re.MULTILINE)
    # Eliminar emojis y símbolos especiales (conservar letras, números y puntuación básica)
    texto = re.sub(r'[^\w\s.,;:!?áéíóúüñÁÉÍÓÚÜÑ\(\)\-]', ' ', texto)
    # Colapsar espacios múltiples y líneas vacías
    texto = re.sub(r'\s{2,}', ' ', texto)
    texto = texto.strip()
    return texto


async def _generar_audio_edge_tts(texto: str) -> bytes:
    """Corrutina asincrona que genera el audio MP3 usando edge-tts."""
    import edge_tts  # Importacion local: solo el servidor web necesita edge_tts
    comunicar = edge_tts.Communicate(texto, VOZ_TTS)
    buffer = BytesIO()
    async for chunk in comunicar.stream():
        if chunk["type"] == "audio":
            buffer.write(chunk["data"])
    return buffer.getvalue()


@csrf_exempt
@require_POST
@xframe_options_exempt
def tts_view(request):
    """
    Endpoint POST /agente-conversacional/tts/
    Recibe: { "text": "texto a sintetizar" }
    Devuelve: audio/mpeg (MP3) generado por edge-tts.
    """
    try:
        texto_raw = request.POST.get('text', '').strip()
        if not texto_raw:
            return JsonResponse({'error': 'Texto vacío.'}, status=400)

        # Limitar longitud para evitar síntesis demasiado larga
        texto_limpio = limpiar_texto_para_tts(texto_raw)
        if len(texto_limpio) > 2000:
            texto_limpio = texto_limpio[:2000] + '.'

        if not texto_limpio:
            return JsonResponse({'error': 'El texto no tiene contenido sintetizable.'}, status=400)

        # Ejecutar la corrutina de edge-tts de forma síncrona en el contexto de Django
        audio_bytes = asyncio.run(_generar_audio_edge_tts(texto_limpio))

        if not audio_bytes:
            return JsonResponse({'error': 'No se generó audio.'}, status=500)

        return HttpResponse(audio_bytes, content_type='audio/mpeg')

    except Exception as e:
        logger.error(f"Error generando TTS: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@xframe_options_exempt
def chat_view(request):
    """
    Renderiza la interfaz del agente conversacional.
    Identifica si el usuario es propietario o cliente basándose en la sesión.
    """
    usuario_id = request.session.get('usuario_id')
    usuario_nombre = request.session.get('usuario_nombre', 'Cliente')
    usuario_rol = request.session.get('usuario_rol', 'cliente')
    
    # Se considera propietario a cualquier usuario logueado en la plataforma (Admin, Vendedor, etc.)
    es_propietario = True if usuario_id else False

    context = {
        'es_propietario': es_propietario,
        'usuario_nombre': usuario_nombre,
        'usuario_rol': usuario_rol,
    }
    return render(request, 'agenteConversacional.html', context)

