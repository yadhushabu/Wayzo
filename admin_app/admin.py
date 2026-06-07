from django.contrib import admin

# Register your models here.
# admin_app/admin.py

from django.contrib import admin
from .models import AuditLog, AdminActionLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):

    list_display = (
        'id',
        'user',
        'action',
        'created_at'
    )

    list_filter = (
        'action',
    )

    search_fields = (
        'user__username',
        'description'
    )


@admin.register(AdminActionLog)
class AdminActionLogAdmin(admin.ModelAdmin):

    list_display = (
        'id',
        'admin',
        'action',
        'target_user',
        'created_at'
    )