from django.contrib import admin
from .models import Conversacion, Mensaje, ProductoEmbedding, AuditoriaHerramienta


@admin.register(Conversacion)
class ConversacionAdmin(admin.ModelAdmin):
    list_display = ('id_conversacion', 'usuario', 'session_key', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('usuario__usuario', 'session_key')
    readonly_fields = ('id_conversacion', 'created_at')
    ordering = ('-created_at',)


@admin.register(Mensaje)
class MensajeAdmin(admin.ModelAdmin):
    list_display = ('conversacion', 'role', 'preview_content', 'created_at')
    list_filter = ('role', 'created_at')
    search_fields = ('content',)
    readonly_fields = ('id_mensaje', 'created_at')
    ordering = ('-created_at',)

    def preview_content(self, obj):
        return obj.content[:80] + '...' if len(obj.content) > 80 else obj.content
    preview_content.short_description = 'Contenido (preview)'


@admin.register(ProductoEmbedding)
class ProductoEmbeddingAdmin(admin.ModelAdmin):
    list_display = ('producto', 'preview_texto', 'updated_at')
    search_fields = ('producto__nombre',)
    readonly_fields = ('id_embedding', 'created_at', 'updated_at')
    ordering = ('-updated_at',)

    def preview_texto(self, obj):
        return obj.texto[:100] + '...' if len(obj.texto) > 100 else obj.texto
    preview_texto.short_description = 'Texto indexado (preview)'


@admin.register(AuditoriaHerramienta)
class AuditoriaHerramientaAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'rol', 'herramienta', 'modelo', 'operacion', 'estado', 'motivo', 'nivel_riesgo', 'cantidad_resultados', 'duracion', 'created_at')
    list_filter = ('rol', 'herramienta', 'estado', 'nivel_riesgo', 'created_at')
    search_fields = ('usuario__usuario', 'modelo', 'operacion', 'motivo')
    readonly_fields = ('id_auditoria', 'created_at')
    ordering = ('-created_at',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

