from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.agency_dashboard, name='agency_dashboard'),
    path('pending/', views.pending_verification, name='pending_verification'),
]
