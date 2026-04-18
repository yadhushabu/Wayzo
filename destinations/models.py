from django.db import models
from django.utils.text import slugify

class Destination(models.Model):

    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)

    description = models.TextField()

    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default="India")

    latitude = models.FloatField()
    longitude = models.FloatField()

    best_season = models.CharField(max_length=200)


    tags = models.CharField(max_length=255)

    avg_budget_per_day = models.IntegerField(null=True, blank=True)

    how_to_reach = models.TextField()

    is_popular = models.BooleanField(default=False)
    image = models.ImageField(upload_to="destinations/", null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    # ✅ FIXED: INSIDE CLASS
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1

            while Destination.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

            self.slug = slug

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    

class Attraction(models.Model):

    destination = models.ForeignKey(
        Destination,
        on_delete=models.CASCADE,
        related_name="attractions"
    )

    name = models.CharField(max_length=200)

    class Meta:
        unique_together = ["destination", "name"]

    description = models.TextField()

    latitude = models.FloatField()
    longitude = models.FloatField()

    # 🔥 PRIORITY
    priority_score = models.IntegerField(default=1)

    # 🔥 TIME
    average_time_needed = models.IntegerField(help_text="Time in minutes")

    # 🔥 BASIC COST
    entry_fee = models.IntegerField(default=0)

    # 🔥 ADVANCED COSTS
    extra_cost_per_person = models.IntegerField(
        default=0,
        help_text="Jeep safari, cruise, activities etc"
    )

    # 🔥 GROUP COST (like boat, private tour)
    group_cost = models.IntegerField(
        default=0,
        help_text="Cost for group activities"
    )

    # 🔥 BEST TIME
    best_time_of_day = models.CharField(
        max_length=50,
        choices=[
            ("morning","Morning"),
            ("afternoon","Afternoon"),
            ("evening","Evening"),
            ("night","Night"), 
            ("any","Any")
        ],
        default="any"
    )

    # 🔥 SEASONAL VISIT
    best_months = models.CharField(
        max_length=100,
        blank=True,
        help_text="e.g. Oct-Mar"
    )

    # 🔥 ACTIVITIES
    activities = models.CharField(
        max_length=255,
        blank=True,
        help_text="jet ski, trekking, cruise, nightlife"
    )

    # 🔥 EXPERIENCE TYPE
    experience_type = models.CharField(
        max_length=100,
        blank=True
    )

    # 🔥 SUITABLE FOR
    suitable_for = models.CharField(
        max_length=100,
        blank=True
    )

    # 🔥 DIFFICULTY (for trekking etc)
    difficulty_level = models.CharField(
        max_length=20,
        choices=[
            ("easy","Easy"),
            ("moderate","Moderate"),
            ("hard","Hard")
        ],
        blank=True
    )

    # 🔥 OPENING HOURS
    opening_time = models.TimeField(null=True, blank=True)
    closing_time = models.TimeField(null=True, blank=True)

    # 🔥 LOCATION DETAILS
    nearest_transport = models.CharField(
        max_length=255,
        blank=True,
        help_text="Nearest airport/railway"
    )

    distance_from_city = models.FloatField(
        null=True,
        blank=True,
        help_text="Distance in KM"
    )

    # 🔥 RULES / SAFETY
    important_rules = models.TextField(blank=True)

    # 🔥 NIGHTLIFE SUPPORT
    is_night_activity = models.BooleanField(default=False)

    # 🔥 IMAGE
    image = models.ImageField(upload_to="attractions/", null=True, blank=True)

    tags = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.name


class AttractionCost(models.Model):
    attraction = models.ForeignKey(
        Attraction,
        on_delete=models.CASCADE,
        related_name="costs"   # 🔥 IMPORTANT
    )

    title = models.CharField(max_length=100)  # Jeep, Cruise, Entry
    price = models.IntegerField()

    def __str__(self):
        return f"{self.title} - ₹{self.price}"