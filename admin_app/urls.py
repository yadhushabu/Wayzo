from django.urls import path
from . import views

app_name = 'admin_app'  # Add app_name for namespacing

urlpatterns = [
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('user/<int:user_id>/', views.user_profile, name='user_profile'),
    path('user/<int:user_id>/toggle-status/', views.toggle_user_status, name='toggle_user_status'),
    path('verify/<int:user_id>/', views.toggle_verification, name='toggle_verification'),
    path("destinations/", views.destination_dashboard, name="admin_destination_dashboard"),
    
]