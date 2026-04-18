from django.db import models
from django.conf import settings
from destinations.models import Destination
from travellers.models import TravelPlan

class Itinerary(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    destination = models.ForeignKey(Destination, on_delete=models.CASCADE)
    preference = models.ForeignKey(TravelPlan, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    total_days = models.IntegerField()
    budget = models.IntegerField(default=0)
    data = models.JSONField(default=dict)  # Store full itinerary data
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class ItineraryDay(models.Model):
    itinerary = models.ForeignKey(Itinerary, on_delete=models.CASCADE, related_name="days")
    day_number = models.IntegerField()
    morning_plan = models.TextField()
    afternoon_plan = models.TextField()
    evening_plan = models.TextField()
    hotel_suggestion = models.TextField(blank=True)
    restaurant_suggestion = models.TextField(blank=True)
    
class CustomizedItinerary(models.Model):
    original_itinerary = models.ForeignKey(Itinerary, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    modified_data = models.JSONField(default=dict)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)