from django.contrib import admin
from .models import RestaurantProfile


@admin.register(RestaurantProfile)
class RestaurantProfileAdmin(admin.ModelAdmin):
    list_display = (
        'restaurant_name',
        'user',
        'mobile',
        'city',
        'state',
        'is_approved'
    )
    list_filter = ('is_approved', 'state', 'city')
    search_fields = ('restaurant_name', 'user__username')


