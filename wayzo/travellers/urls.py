from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.traveller_dashboard, name='traveller_dashboard'),
]
