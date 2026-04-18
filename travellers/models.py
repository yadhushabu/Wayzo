

# Create your models here.
from datetime import timedelta

from django.db import models
from django.conf import settings

from destinations.models import Destination


class TravellerProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    mobile = models.CharField(max_length=15)
    age = models.PositiveIntegerField()
    gender = models.CharField(
        max_length=10,
        choices=(('male','Male'),('female','Female'),('other','Other'))
    )
    is_private = models.BooleanField(default=False)
    address=models.TextField()
    city=models.CharField(max_length=20)
    state=models.CharField(max_length=20)
    profile_picture = models.ImageField(
        upload_to="traveller_profiles/",
        blank=True,
        null=True
    )

    def __str__(self):
        return self.first_name




from django.db import models
from django.contrib.auth.models import User
from agencies.models import TourPackage


class Wishlist(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    package = models.ForeignKey(TourPackage, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)


class ProfilePost(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile_posts")

    caption = models.TextField(blank=True)
    image = models.ImageField(upload_to="profile_posts/", blank=True, null=True)

    location = models.CharField(max_length=255, blank=True)  # optional: place visited

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.caption[:20]}"


class CompletedTrip(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="completed_trips")

    trip_name = models.CharField(max_length=255)
    location = models.CharField(max_length=255)

    start_date = models.DateField()
    end_date = models.DateField()

    is_shared = models.BooleanField(default=False)  # 🔥 user choice

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.trip_name}"


class Follow(models.Model):
    follower = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="following")
    following = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="followers")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('follower', 'following')

    def __str__(self):
        return f"{self.follower} → {self.following}"

class ProfilePostLike(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    post = models.ForeignKey(ProfilePost, on_delete=models.CASCADE, related_name="likes")

    class Meta:
        unique_together = ['user', 'post']


class ProfileComment(models.Model):
    post = models.ForeignKey(ProfilePost, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


from restaurants.models import RestaurantProfile

class PropertyBooking(models.Model):

    BOOKING_TYPE = (
        ("room", "Room Booking"),
        ("table", "Table Booking"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    property = models.ForeignKey(RestaurantProfile, on_delete=models.CASCADE)

    booking_type = models.CharField(max_length=10, choices=BOOKING_TYPE)

    # Common fields
    booking_date = models.DateField()
    time = models.TimeField(null=True, blank=True)

    guests = models.PositiveIntegerField()

    # For hotels/resorts/homestay
    check_in = models.DateField(null=True, blank=True)
    check_out = models.DateField(null=True, blank=True)
    rooms = models.PositiveIntegerField(null=True, blank=True)

    # Status
    status = models.CharField(
        max_length=20,
        choices=(
            ("pending", "Pending"),
            ("confirmed", "Confirmed"),
            ("cancelled", "Cancelled"),
        ),
        default="pending"
    )

    special_request = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.property} - {self.booking_type}"
    


# travellers/models.py

# models.py
from django.db import models
from django.conf import settings

class TripPlan(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    destination = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField()

    adults = models.IntegerField()
    children = models.IntegerField()

    budget = models.CharField(max_length=50)
    interests = models.JSONField()

    # ✅ ADD THESE MISSING FIELDS
    stay_type = models.CharField(max_length=50, blank=True, null=True)
    food_type = models.CharField(max_length=50, blank=True, null=True)
    travel_style = models.CharField(max_length=50, blank=True, null=True)
    transport = models.CharField(max_length=50, blank=True, null=True)
    trip_type = models.CharField(max_length=50, blank=True, null=True)
    special_requests = models.TextField(blank=True, null=True)
    
    # Optional: Add these if you want to save them too
    room_type = models.CharField(max_length=50, blank=True, null=True)
    amenities = models.JSONField(blank=True, null=True, default=list)
    cuisines = models.JSONField(blank=True, null=True, default=list)

    generated_plan = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)
    ai_model_used = models.CharField(max_length=50, default="gemini-1.5-flash")
    generation_time_seconds = models.FloatField(null=True, blank=True)
    plan_html = models.TextField(blank=True, null=True)  # Rich HTML version
    context_data = models.JSONField(blank=True, null=True)  # Save input for re-generation
    

    def __str__(self):
        return f"{self.user} - {self.destination}"
    

from django.db import models
from django.conf import settings
from datetime import timedelta
from destinations.models import Destination


from django.db import models
from django.conf import settings
from datetime import timedelta


class TravelPlan(models.Model):

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="travel_plans"
    )

    destination = models.ForeignKey(
    'destinations.Destination',
    on_delete=models.CASCADE,
    related_name="travel_plans"
)

    # 🔹 Trip type
    travel_type = models.CharField(
        max_length=50,
        choices=[
            ("solo", "Solo"),
            ("couple", "Couple"),
            ("family", "Family"),
            ("friends", "Friends")
        ]
    )

    mood = models.CharField(
        max_length=50,
        choices=[
            ("relaxed", "Relaxed"),
            ("adventure", "Adventure"),
            ("honeymoon", "Honeymoon"),
            ("spiritual", "Spiritual"),
            ("luxury", "Luxury")
        ]
    )

    # 🔹 Group details
    adults = models.PositiveIntegerField(default=1)
    children = models.PositiveIntegerField(default=0)

    # 🔹 Budget
    budget_range = models.CharField(
        max_length=50,
        choices=[
            ("budget", "Budget"),
            ("mid", "Mid"),
            ("luxury", "Luxury")
        ]
    )

    daily_budget = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )

    # 🔹 Duration
    number_of_days = models.PositiveIntegerField()
    start_date = models.DateField(null=True, blank=True)

    # 🔹 Time control
    start_time = models.TimeField(default="09:00")
    end_time = models.TimeField(default="21:00")

    # 🔹 Locations
    start_location_name = models.CharField(max_length=255, blank=True)
    start_latitude = models.FloatField(null=True, blank=True)
    start_longitude = models.FloatField(null=True, blank=True)

    end_location_name = models.CharField(max_length=255, blank=True)
    end_latitude = models.FloatField(null=True, blank=True)
    end_longitude = models.FloatField(null=True, blank=True)

    # 🔹 Transport
    transport_mode = models.CharField(
        max_length=50,
        choices=[
            ("bus", "Bus"),
            ("train", "Train"),
            ("car", "Car"),
            ("bike", "Bike"),
            ("walk", "Walk")
        ],
        default="car"
    )

    pace = models.CharField(
        max_length=20,
        choices=[
            ("slow", "Relaxed"),
            ("medium", "Balanced"),
            ("fast", "Aggressive")
        ],
        default="medium"
    )

    # 🔥 STAY PREFERENCES
    stay_type = models.CharField(
        max_length=50,
        choices=[
            ("hotel", "Hotel"),
            ("resort", "Resort"),
            ("homestay", "Homestay"),
            ("hostel", "Hostel"),
            ("any", "Any")
        ],
        default="any"
    )

    room_type = models.CharField(
        max_length=50,
        choices=[
            ("standard", "Standard"),
            ("deluxe", "Deluxe"),
            ("suite", "Suite")
        ],
        blank=True
    )

    # 🔥 FOOD PREFERENCES
    food_preference = models.CharField(
        max_length=50,
        choices=[
            ("veg", "Vegetarian"),
            ("nonveg", "Non-Vegetarian"),
            ("vegan", "Vegan"),
            ("any", "Any")
        ],
        default="any"
    )

    cuisine_preference = models.CharField(
        max_length=100,
        blank=True
    )

    meal_budget = models.CharField(
        max_length=50,
        choices=[
            ("low", "Budget"),
            ("medium", "Moderate"),
            ("high", "Premium")
        ],
        default="medium"
    )

    # 🔥 ACTIVITIES
    activity_types = models.CharField(
        max_length=200,
        blank=True,
        help_text="e.g. sightseeing, trekking, beach"
    )

    must_visit_places = models.TextField(blank=True)

    # 🔥 TRAVEL LIMITS
    max_travel_distance_per_day = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="In KM"
    )

    avoid_long_travel = models.BooleanField(default=False)

    # 🔥 SPECIAL CONDITIONS
    has_elderly = models.BooleanField(default=False)
    needs_accessibility = models.BooleanField(default=False)

    # 🔥 WEATHER / FLEXIBILITY
    prefer_indoor = models.BooleanField(default=False)
    rain_flexible = models.BooleanField(default=True)

    # 🔥 EXPERIENCE STYLE
    nightlife_preference = models.BooleanField(default=False)

    crowd_preference = models.CharField(
        max_length=20,
        choices=[
            ("low", "Less crowded"),
            ("medium", "Balanced"),
            ("high", "Lively")
        ],
        default="medium"
    )

    # 🔥 FUTURE FEATURES
    auto_book_stays = models.BooleanField(default=False)
    auto_book_restaurants = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    # ✅ Derived
    @property
    def number_of_nights(self):
        return max(0, self.number_of_days - 1)

    @property
    def end_date(self):
        if self.start_date:
            return self.start_date + timedelta(days=self.number_of_days - 1)
        return None

    def __str__(self):
        return f"{self.user} - {self.destination} ({self.number_of_days} days)"