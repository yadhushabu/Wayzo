

# Create your models here.
from datetime import timedelta

from django.db import models
from django.conf import settings

from restaurants.models import RestaurantProfile




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
    cover_image = models.ImageField(
        upload_to="traveller_covers/",
        blank=True,
        null=True
    )

    def __str__(self):
        return self.first_name




from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()
from agencies.models import TourPackage




class Wishlist(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wishlist_items')
    package = models.ForeignKey('agencies.TourPackage', on_delete=models.CASCADE, null=True, blank=True)
    restaurant = models.ForeignKey('restaurants.RestaurantProfile', on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = [['user', 'package'], ['user', 'restaurant']]
    
    def __str__(self):
        if self.package:
            return f"{self.user.username} - {self.package.title}"
        return f"{self.user.username} - {self.restaurant.restaurant_name}"


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
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'post']


class ProfileComment(models.Model):
    post = models.ForeignKey(ProfilePost, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.text[:30]}"
    

class BuddyRequest(models.Model):
    """Model for buddy requests between travellers"""
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    )
    
    from_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_buddy_requests')
    to_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_buddy_requests')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['from_user', 'to_user']
    
    def __str__(self):
        return f"{self.from_user} → {self.to_user} ({self.status})"