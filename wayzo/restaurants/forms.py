
from django import forms
from .models import RestaurantProfile

class RestaurantProfileEditForm(forms.ModelForm):

    class Meta:
        model = RestaurantProfile
        fields = [
            "description",
            "property_type",
            "opening_time",
            "closing_time",
            "checkin_time",
            "checkout_time",
            "cuisine_type",
            "food_type",
            "menu_file",
            "total_rooms",
            "room_type",
            "price_range",
            "wifi",
            "parking",
            "air_conditioning",
            "swimming_pool",
            "live_music",
            "pet_friendly",
            "room_service",
            "breakfast_availabe",
            "restaurant_available",
            "gym",
            "taxi_service",
            "website",
            "instagram",
        ]
