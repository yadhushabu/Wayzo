from django import forms
from .models import RestaurantProfile


class RestaurantProfileEditForm(forms.ModelForm):

    class Meta:
        model = RestaurantProfile
        fields = [
            # 🔹 BASIC INFO
            "description",

            # 🔥 NEW IMPORTANT FIELDS
            "category",
            "price_level",
            "avg_cost_per_person",
            "rating",
            "is_popular",
            "recommended_for",

            # 🔹 TIMINGS
            "opening_time",
            "closing_time",
            "checkin_time",
            "checkout_time",

            # 🔹 FOOD
            "cuisine_type",
            "food_type",
            "menu_file",

            # 🔹 ROOMS
            "total_rooms",
            "room_type",

            # 🔹 KEEP OLD (for compatibility)
            "price_range",

            # 🔹 AMENITIES
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

            # 🔹 LOCATION IMPROVEMENTS (OPTIONAL BUT IMPORTANT)
            "area",
            "latitude",
            "longitude",

            # 🔹 SOCIAL
            "website",
            "instagram",
        ]

        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),

            "recommended_for": forms.TextInput(attrs={
                "placeholder": "family / couples / friends"
            }),

            "avg_cost_per_person": forms.NumberInput(attrs={
                "placeholder": "Approx cost per person"
            }),

            "latitude": forms.NumberInput(attrs={"step": "any"}),
            "longitude": forms.NumberInput(attrs={"step": "any"}),

            "opening_time": forms.TimeInput(attrs={"type": "time"}),
            "closing_time": forms.TimeInput(attrs={"type": "time"}),
            "checkin_time": forms.TimeInput(attrs={"type": "time"}),
            "checkout_time": forms.TimeInput(attrs={"type": "time"}),
        }

    # 🔥 CLEANING (IMPORTANT)
    def clean_rating(self):
        rating = self.cleaned_data.get("rating")
        if rating and (rating < 0 or rating > 5):
            raise forms.ValidationError("Rating must be between 0 and 5")
        return rating

    def clean_avg_cost_per_person(self):
        cost = self.cleaned_data.get("avg_cost_per_person")
        if cost and cost < 0:
            raise forms.ValidationError("Cost cannot be negative")
        return cost