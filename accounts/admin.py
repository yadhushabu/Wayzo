from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):

    # ✅ Columns shown in list page
    list_display = (
        'id',
        'username',
        'email',
        'role',
        'is_verified',
        'is_staff',
        'get_display_name',
        'get_phone'
    )

    # ✅ Filters (right side)
    list_filter = ('role', 'is_verified', 'is_staff', 'is_superuser')

    # ✅ Search bar
    search_fields = ('username', 'email', 'first_name', 'last_name')

    # ✅ Default ordering
    ordering = ('-id',)

    # ✅ Field grouping in edit page
    fieldsets = UserAdmin.fieldsets + (
        ("Custom Info", {
            'fields': ('role', 'is_verified', 'profile_picture')
        }),
    )

    # ✅ Add user form fields
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Custom Info", {
            'fields': ('role', 'email', 'profile_picture')
        }),
    )

    # ✅ Read-only (optional)
    readonly_fields = ('get_display_name',)

    # ✅ Optional: show image preview
    def profile_preview(self, obj):
        if obj.profile_picture:
            return f'<img src="{obj.profile_picture.url}" width="40" height="40" style="border-radius:50%;" />'
        return "No Image"
    
    profile_preview.allow_tags = True
    profile_preview.short_description = "Profile"
