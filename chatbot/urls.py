from django.urls import path
from . import views
app_name = "chatbot"


urlpatterns = [
    path('', views.chatbot_page, name='chatbot_page'),
    path('send/', views.send_message, name='send_message'),
    path('history/<int:session_id>/', views.get_chat_history, name='chat_history'),
    path('clear/', views.clear_chat, name='clear_chat'),
    path('sessions/', views.get_sessions, name='chat_sessions'),
]