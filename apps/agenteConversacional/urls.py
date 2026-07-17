from django.urls import path
from . import views

app_name = 'agenteConversacional'

urlpatterns = [
    path('', views.chat_view, name='chat'),
    path('tts/', views.tts_view, name='tts'),
]
