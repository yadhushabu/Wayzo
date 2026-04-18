from django.db import models
from django.conf import settings
from multiselectfield import MultiSelectField

from django.db import models
from django.conf import settings
from multiselectfield import MultiSelectField


class RestaurantProfile(models.Model):

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    # 🔹 BASIC
    restaurant_name = models.CharField(max_length=200)

    property_type = models.CharField(
        max_length=50,
        choices=[
            ("Restaurant","Restaurant"),
            ("Hotel","Hotel"),
            ("Resort","Resort"),
            ("Homestay","Homestay"),
            ("Cafe","Cafe")
        ]
    )

    # 🔥 NEW (IMPORTANT)
    CATEGORY_CHOICES = [
        ("stay", "Stay"),
        ("restaurant", "Restaurant"),
        ("cafe", "Cafe"),
        ("both", "Stay + Food"),
    ]

    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default="restaurant"
    )

    # 🔹 LEGAL
    fssai_license_number = models.CharField(max_length=200)
    license_document = models.FileField(upload_to='licenses/')
    id_proof = models.FileField(upload_to='id_proofs/')

    # 🔹 LOCATION
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)

    # 🔥 NEW LOCATION IMPROVEMENTS
    area = models.CharField(max_length=100, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    mobile = models.CharField(max_length=20)

    # 🔹 DESCRIPTION
    description = models.TextField(blank=True)

    # 🔹 TIMINGS
    opening_time = models.TimeField(null=True, blank=True)
    closing_time = models.TimeField(null=True, blank=True)

    checkin_time = models.TimeField(null=True, blank=True)
    checkout_time = models.TimeField(null=True, blank=True)

    # 🔹 CUISINE (KEEP OLD FOR NOW)
    CUISINE_CHOICES = [
        ("Kerala", "Kerala"),
        ("South_indian", "South Indian"),
        ("North_indian", "North Indian"),
        ("Indian", "Indian"),
        ("Chinese", "Chinese"),
        ("Arabic", "Arabic"),
        ("Continental", "Continental"),
        ("Italian", "Italian"),
        ("Thai", "Thai"),
        ("Seafood", "Seafood"),
        ("Fast_food", "Fast Food"),
        ("Street_food", "Street Food"),
        ("Bakery", "Bakery"),
        ("Cafe", "Cafe"),
        ("Multi_cuisine", "Multi Cuisine"),
    ]

    cuisine_type = MultiSelectField(choices=CUISINE_CHOICES, blank=True)

    food_type = models.CharField(
        max_length=20,
        choices=[
            ("Veg","Veg"),
            ("Non Veg","Non Veg"),
            ("Veg & Non Veg","Veg & Non Veg")
        ],
        blank=True
    )

    # 🔥 NEW PRICE SYSTEM (DON'T REMOVE OLD)
    price_range = models.CharField(max_length=100, blank=True)

    PRICE_LEVEL_CHOICES = [
        (1, "Budget"),
        (2, "Mid"),
        (3, "Luxury"),
    ]

    price_level = models.IntegerField(
        choices=PRICE_LEVEL_CHOICES,
        default=2
    )

    # 🔥 NEW QUALITY METRICS
    rating = models.FloatField(default=4.0)
    reviews_count = models.IntegerField(default=0)

    avg_cost_per_person = models.IntegerField(null=True, blank=True)

    # 🔥 AI HELPER FIELDS
    is_popular = models.BooleanField(default=False)

    recommended_for = models.CharField(
        max_length=100,
        blank=True
    )  # family, couples, friends

    # 🔹 FACILITIES
    wifi = models.BooleanField(default=False)
    parking = models.BooleanField(default=False)
    air_conditioning = models.BooleanField(default=False)
    swimming_pool = models.BooleanField(default=False)
    live_music = models.BooleanField(default=False)
    pet_friendly = models.BooleanField(default=False)
    room_service = models.BooleanField(default=False)
    breakfast_availabe = models.BooleanField(default=False)
    restaurant_available = models.BooleanField(default=False)
    gym = models.BooleanField(default=False)
    taxi_service = models.BooleanField(default=False)

    # 🔹 ROOMS
    total_rooms = models.IntegerField(null=True, blank=True)
    room_type = models.CharField(null=True, blank=True)

    # 🔹 MEDIA
    menu_file = models.FileField(upload_to="menus/", blank=True, null=True)

    room_image = models.ImageField(upload_to='restaurant/sections/rooms/', null=True, blank=True)
    entrance_image = models.ImageField(upload_to='restaurant/sections/entrance/', null=True, blank=True)
    cafeteria_image = models.ImageField(upload_to='restaurant/sections/cafeteria/', null=True, blank=True)
    parking_image = models.ImageField(upload_to='restaurant/sections/parking/', null=True, blank=True)
    activities_image = models.ImageField(upload_to='restaurant/sections/activities/', null=True, blank=True)

    # 🔹 SOCIAL
    website = models.URLField(blank=True)
    instagram = models.URLField(blank=True)

    # 🔹 STATUS
    is_approved = models.BooleanField(default=False)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.restaurant_name

class RestaurantGallery(models.Model):

    SECTION_CHOICES = [
        ("rooms", "Rooms"),
        ("entrance", "Entrance"),
        ("cafeteria", "Cafeteria"),
        ("parking", "Parking"),
        ("activities", "Activities"),
    ]

    restaurant = models.ForeignKey(
        RestaurantProfile,
        on_delete=models.CASCADE,
        related_name="gallery"
    )

    section = models.CharField(
        max_length=50,
        choices=SECTION_CHOICES
    )

    image = models.ImageField(upload_to="restaurant_gallery/")