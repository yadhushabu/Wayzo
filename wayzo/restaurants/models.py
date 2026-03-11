from django.db import models
from django.conf import settings

class RestaurantProfile(models.Model):

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    # REGISTRATION FIELDS (NOT EDITABLE)
    restaurant_name = models.CharField(max_length=200)
    fssai_license_number = models.CharField(max_length=200)
    license_document = models.FileField(upload_to='licenses/')
    place_id_proof = models.FileField(upload_to='id_proofs/')
    mobile = models.CharField(max_length=20)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)

    # EDITABLE BUSINESS DETAILS
    description = models.TextField(blank=True)

    property_type = models.CharField(
        max_length=50,
        choices=[
            ("Restaurant","Restaurant"),
            ("Hotel","Hotel"),
            ("Resort","Resort"),
            ("Homestay","Homestay"),
            ("Cafe","Cafe")
        ],
        blank=True
    )

    opening_time = models.TimeField(null=True, blank=True)
    closing_time = models.TimeField(null=True, blank=True)

    checkin_time = models.TimeField(null=True, blank=True)
    checkout_time = models.TimeField(null=True, blank=True)

    cuisine_type = models.CharField(
                max_length=30,
                blank=True,
                choices=[
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
                )

    food_type = models.CharField(
        max_length=20,
        choices=[
            ("Veg","Veg"),
            ("Non Veg","Non Veg"),
            ("Veg & Non Veg","Veg & Non Veg")
        ],
        blank=True
    )

    menu_file = models.FileField(upload_to="menus/", blank=True, null=True)

    total_rooms = models.IntegerField(null=True, blank=True)
    room_type = models.CharField(null=True, blank=True)

    price_range = models.CharField(max_length=100, blank=True)

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


    website = models.URLField(blank=True)
    instagram = models.URLField(blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.restaurant_name

    # ✅ Section Images (Optional)
    room_image = models.ImageField(
        upload_to='restaurant/sections/rooms/',
        null=True,
        blank=True
    )

    entrance_image = models.ImageField(
        upload_to='restaurant/sections/entrance/',
        null=True,
        blank=True
    )

    cafeteria_image = models.ImageField(
        upload_to='restaurant/sections/cafeteria/',
        null=True,
        blank=True
    )

    parking_image = models.ImageField(
        upload_to='restaurant/sections/parking/',
        null=True,
        blank=True
    )

    activities_image = models.ImageField(
        upload_to='restaurant/sections/activities/',
        null=True,
        blank=True
    ) 

    is_approved = models.BooleanField(default=False)

    def __str__(self):
        return self.restaurant_name
    

SECTION_CHOICES = (
    ('rooms', 'Rooms'),
    ('entrance', 'Entrance'),
    ('cafeteria', 'Cafeteria'),
    ('parking', 'Parking'),
    ('activities', 'Activities'),
)


class RestaurantGallery(models.Model):
    restaurant = models.ForeignKey(
        RestaurantProfile,
        on_delete=models.CASCADE,
        related_name='gallery'
    )

    section = models.CharField(
        max_length=20,
        choices=SECTION_CHOICES
    )

    image = models.ImageField(
        upload_to='restaurant/gallery/'
    )

    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.restaurant.restaurant_name} - {self.section}"

