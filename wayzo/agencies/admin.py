

# Register your models here.
from django.contrib import admin
from .models import AgencyProfile

@admin.register(AgencyProfile)
class AgencyProfileAdmin(admin.ModelAdmin):
    list_display = (
        'agency_name',
        'user',
        'mobile',
        'city',
        'state',
        'is_approved'
    )
    list_filter = ('is_approved', 'state', 'city')
    search_fields = ('agency_name', 'user__username')
