# planner/models.py

from django.db import models

from django.conf import settings


# =========================================================
# 🔥 TRIP REQUEST MODEL
# =========================================================

class TripRequest(models.Model):
    """
    Stores traveler preferences + trip personalization
    """

    # =====================================================
    # BASIC TRIP INFO
    # =====================================================

    destination = models.CharField(
        max_length=200
    )

    days = models.IntegerField(
        default=3
    )

    interests = models.TextField(
        help_text=(
            "nature, beaches, adventure, nightlife, "
            "culture, food, trekking etc."
        )
    )

    starting_place = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Trip starting location"
    )

    ending_place = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Trip ending location"
    )

    # =====================================================
    # TRAVELER PERSONALIZATION
    # =====================================================

    traveler_name = models.CharField(
        max_length=120,
        blank=True,
        null=True
    )

    traveler_type = models.CharField(
        max_length=50,
        choices=[
            ('solo', 'Solo Traveler'),
            ('couple', 'Couple'),
            ('family', 'Family'),
            ('friends', 'Friends Group'),
            ('business', 'Business'),
        ],
        default='solo'
    )

    # =====================================================
    # BUDGET
    # =====================================================

    budget = models.CharField(
        max_length=30,
        choices=[
            ('budget', 'Budget'),
            ('mid_range', 'Mid Range'),
            ('luxury', 'Luxury'),
        ],
        default='mid_range'
    )

    # =====================================================
    # HOTEL PREFERENCES
    # =====================================================

    hotel_type = models.CharField(
        max_length=50,
        choices=[
            ('hotel', 'Hotel'),
            ('resort', 'Resort'),
            ('villa', 'Villa'),
            ('hostel', 'Hostel'),
            ('homestay', 'Homestay'),
        ],
        blank=True,
        null=True
    )

    hotel_stars = models.IntegerField(
        default=4
    )

    # =====================================================
    # FOOD PREFERENCES
    # =====================================================

    food_preference = models.CharField(
        max_length=50,
        choices=[
            ('veg', 'Vegetarian'),
            ('non_veg', 'Non Vegetarian'),
            ('vegan', 'Vegan'),
            ('halal', 'Halal'),
            ('any', 'Any'),
        ],
        default='any'
    )

    # =====================================================
    # ACTIVITY STYLE
    # =====================================================

    activity_level = models.CharField(
        max_length=50,
        choices=[
            ('relaxed', 'Relaxed'),
            ('moderate', 'Moderate'),
            ('active', 'Active'),
        ],
        default='moderate'
    )

    # =====================================================
    # TRAVEL TIMING
    # =====================================================

    start_date = models.DateField(
        blank=True,
        null=True
    )

    # =====================================================
    # TRANSPORT PREFERENCE
    # =====================================================

    transport_mode = models.CharField(
        max_length=50,
        choices=[
            ('car', 'Car'),
            ('bike', 'Bike'),
            ('walking', 'Walking'),
            ('public_transport', 'Public Transport'),
            ('mixed', 'Mixed'),
        ],
        default='mixed'
    )

    # =====================================================
    # SPECIAL OPTIONS
    # =====================================================

    include_hidden_gems = models.BooleanField(
        default=True
    )

    include_nightlife = models.BooleanField(
        default=False
    )

    include_shopping = models.BooleanField(
        default=False
    )

    include_local_food = models.BooleanField(
        default=True
    )

    # =====================================================
    # AI CUSTOM NOTES
    # =====================================================

    special_requirements = models.TextField(
        blank=True,
        null=True,
        help_text=(
            "Wheelchair accessibility, kids friendly, "
            "honeymoon trip, photography spots etc."
        )
    )

    # =====================================================
    # SYSTEM
    # =====================================================

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    # =====================================================
    # STRING
    # =====================================================

    def __str__(self):

        return (
            f"{self.destination} | "
            f"{self.days} days | "
            f"{self.traveler_type}"
        )


# =========================================================
# 🔥 GENERATED ITINERARY MODEL
# =========================================================

class Itinerary(models.Model):
    """
    Stores generated AI itinerary
    """

    trip_request = models.OneToOneField(
        TripRequest,
        on_delete=models.CASCADE,
        related_name='itinerary'
    )

    # =====================================================
    # GENERATED JSON DATA
    # =====================================================

    data = models.JSONField()

    # =====================================================
    # AI SUMMARY
    # =====================================================

    summary = models.TextField(
        blank=True,
        null=True
    )

    # =====================================================
    # ESTIMATED COST
    # =====================================================

    estimated_budget = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    # =====================================================
    # SHAREABLE FEATURES
    # =====================================================

    is_public = models.BooleanField(
        default=False
    )

    share_token = models.CharField(
        max_length=120,
        blank=True,
        null=True
    )

    # =====================================================
    # EXPORTS
    # =====================================================

    pdf_generated = models.BooleanField(
        default=False
    )

    # =====================================================
    # USER FEEDBACK
    # =====================================================

    traveler_rating = models.FloatField(
        blank=True,
        null=True
    )

    traveler_feedback = models.TextField(
        blank=True,
        null=True
    )

    # =====================================================
    # SYSTEM
    # =====================================================

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    # =====================================================
    # STRING
    # =====================================================

    def __str__(self):

        return (
            f"Itinerary for "
            f"{self.trip_request.destination}"
        )


class SavedItinerary(models.Model):

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    itinerary_json = models.JSONField()

    updated_at = models.DateTimeField(auto_now=True)

    created_at = models.DateTimeField(auto_now_add=True)

    title = models.CharField(max_length=255, blank=True, null=True)

    destination = models.CharField(max_length=255)

    days = models.IntegerField(default=1)

    def __str__(self):
        return f"{self.user} - {self.destination}"