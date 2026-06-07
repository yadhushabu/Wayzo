from django.urls import path
from . import views

app_name = 'admin_app'  # Add app_name for namespacing

urlpatterns = [
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('user/<int:user_id>/', views.user_profile, name='user_profile'),
    path('user/<int:user_id>/toggle-status/', views.toggle_user_status, name='toggle_user_status'),
    path('verify/<int:user_id>/', views.toggle_verification, name='toggle_verification'),
    path(
        "approvals/",
        views.admin_approvals,
        name="admin_approvals"
    ),
    path(
        "users/",
        views.user_management,
        name="user_management"
    ),
    
    path(
        "audit-logs/",
        views.audit_logs,
        name="audit_logs"
    ),

    path(
        "audit-logs/export/",
        views.audit_logs_export,
        name="audit_logs_export"
    ),
]