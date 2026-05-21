

# Create your models here.
from datetime import timedelta

from django.db import models
from django.conf import settings




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
    

