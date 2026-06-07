from django.db import models
from django.conf import settings
from django.utils import timezone
from .services.ranking_engine import RankingEngine
from datetime import datetime
from django.db.models import Avg


# =========================================================
# APPROVAL MIXIN
# =========================================================

class ApprovalMixin(models.Model):

    is_approved = models.BooleanField(
        default=False
    )

    class Meta:
        abstract = True

    def auto_approve(self):

        created_by = getattr(
            self,
            "created_by",
            None
        )

        if (
            created_by and
            (
                created_by.is_staff or
                created_by.is_superuser
            )
        ):
            self.is_approved = True

    def save(self, *args, **kwargs):

        self.auto_approve()

        super().save(*args, **kwargs)


# =========================================================
# DESTINATION
# =========================================================

class Destination(ApprovalMixin):

    # =====================================================
    # SEASONS
    # =====================================================

    SEASON_CHOICES = [
        ("spring", "Spring"),
        ("summer", "Summer"),
        ("autumn", "Autumn"),
        ("winter", "Winter"),
        ("year_round", "Year Round"),
    ]

    WEATHER_CHOICES = [
        ("sunny", "Sunny"),
        ("cold", "Cold"),
        ("rainy", "Rainy"),
        ("snow", "Snow"),
        ("cloudy", "Cloudy"),
    ]

    # =====================================================
    # BASIC INFO
    # =====================================================

    name = models.CharField(
        max_length=150,
        unique=True
    )

    description = models.TextField()

    country = models.CharField(
        max_length=100,
        blank=True
    )

    state = models.CharField(
        max_length=100,
        blank=True
    )

    city = models.CharField(
        max_length=100,
        blank=True
    )

    # =====================================================
    # LOCATION
    # =====================================================

    latitude = models.FloatField(
        blank=True,
        null=True
    )

    longitude = models.FloatField(
        blank=True,
        null=True
    )

    # =====================================================
    # BEST TIME
    # =====================================================

    best_season = models.CharField(
        max_length=50,
        choices=SEASON_CHOICES,
        blank=True
    )


    best_month_start = models.IntegerField(
        default=1
    )

    best_month_end = models.IntegerField(
        default=12
    )

    preferred_weather = models.CharField(
        max_length=50,
        choices=WEATHER_CHOICES,
        blank=True
    )

    # =====================================================
    # WEATHER CACHE
    # =====================================================

    current_temperature = models.FloatField(
        blank=True,
        null=True
    )

    weather_condition = models.CharField(
        max_length=100,
        blank=True
    )

    humidity = models.FloatField(
        blank=True,
        null=True
    )

    weather_score = models.FloatField(
        default=10
    )

    last_weather_updated = models.DateTimeField(
        blank=True,
        null=True
    )

    # =====================================================
    # AI RANKING SCORES
    # =====================================================

    manual_priority_score = models.FloatField(
        default=10,
        help_text="Admin/User controlled importance score (0-20)"
    )

    weather_score = models.FloatField(
        default=10
    )

    seasonal_score = models.FloatField(
        default=10
    )

    popularity_score = models.FloatField(
        default=0
    )

    usage_score = models.FloatField(
        default=0
    )

    rating_score = models.FloatField(
        default=0
    )

    final_trending_score = models.FloatField(
        default=0
    )

    recommended_visit_order = models.IntegerField(
        default=0
    )

    # =====================================================
    # FLAGS
    # =====================================================

    is_featured = models.BooleanField(
        default=False
    )

    # =====================================================
    # STATS
    # =====================================================

    total_views = models.PositiveIntegerField(
        default=0
    )

    total_itinerary_usage = models.PositiveIntegerField(
        default=0
    )

    total_reviews = models.PositiveIntegerField(
        default=0
    )

    average_rating = models.FloatField(
        default=0
    )

    # =====================================================
    # USER
    # =====================================================

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    # =====================================================
    # WEATHER SCORE
    # =====================================================

    def calculate_weather_score(self):

        if not self.current_temperature:
            return 10

        temp = self.current_temperature

        score = 0

        # Ideal tourism temperature
        if 20 <= temp <= 30:
            score += 20

        elif 15 <= temp < 20 or 30 < temp <= 35:
            score += 14

        else:
            score += 6

        # Weather condition bonus
        weather = (self.weather_condition or "").lower()

        if "clear" in weather or "sunny" in weather:
            score += 5

        elif "cloud" in weather:
            score += 3

        elif "rain" in weather:
            score -= 4

        elif "storm" in weather:
            score -= 8

        # Humidity penalty
        if self.humidity and self.humidity > 85:
            score -= 3

        return max(score, 0)


    # =====================================================
    # SEASONAL SCORE
    # =====================================================

    def calculate_season_score(self):

        current_month = datetime.now().month

        start = self.best_month_start
        end = self.best_month_end

        if start <= end:

            if start <= current_month <= end:
                return 20

        else:

            if current_month >= start or current_month <= end:
                return 20

        return 6


    # =====================================================
    # POPULARITY SCORE
    # =====================================================

    def calculate_popularity_score(self):

        score = 0

        # Reviews
        score += min(self.total_reviews * 0.15, 10)

        # Average rating
        score += self.average_rating * 3

        # Views
        score += min(self.total_views * 0.003, 8)

        # Itinerary usage
        score += min(self.total_itinerary_usage * 0.05, 10)

        # Featured boost
        if self.is_featured:
            score += 5

        return min(score, 35)


    # =====================================================
    # RATING SCORE
    # =====================================================

    def calculate_rating_score(self):

        return self.average_rating * 4


    # =====================================================
    # USAGE SCORE
    # =====================================================

    def calculate_usage_score(self):

        return min(
            self.total_itinerary_usage * 0.1,
            10
        )


    # =====================================================
    # FINAL AI SCORE
    # =====================================================

    def update_scores(self):

        self.weather_score = self.calculate_weather_score()

        self.seasonal_score = self.calculate_season_score()

        self.popularity_score = self.calculate_popularity_score()

        self.rating_score = self.calculate_rating_score()

        self.usage_score = self.calculate_usage_score()

        self.final_trending_score = round(

            self.manual_priority_score +

            self.weather_score +

            self.seasonal_score +

            self.popularity_score +

            self.rating_score +

            self.usage_score,

            2
        )

    def refresh_review_stats(self):

        self.total_reviews = self.reviews.count()

        self.average_rating = (
            self.reviews.aggregate(
                Avg("rating")
            )["rating__avg"] or 0
        )

        self.save()


    # =====================================================
    # SAVE
    # =====================================================

    def save(self, *args, **kwargs):

        # Auto weather sync
        from .services.weather_service import WeatherService

        weather = WeatherService.get_weather(
            self.city or self.name
        )

        if weather:

            self.current_temperature = weather["temp"]

            self.weather_condition = weather["description"]

            self.humidity = weather["humidity"]

            self.last_weather_updated = timezone.now()

        self.update_scores()

        super().save(*args, **kwargs)

    # =====================================================
    # DISPLAY
    # =====================================================

    def is_best_time_now(self):

        current_month = datetime.now().month

        start = self.best_month_start
        end = self.best_month_end

        if start <= end:
            return start <= current_month <= end

        return (
            current_month >= start or
            current_month <= end
        )

    def get_current_month_status(self):

        if self.is_best_time_now():
            return "🔥 Best time to visit now"

        return "📅 Off season currently"

    def __str__(self):

        return self.name


# =========================================================
# DESTINATION IMAGES
# =========================================================

class DestinationImage(models.Model):

    destination = models.ForeignKey(
        Destination,
        on_delete=models.CASCADE,
        related_name="images"
    )

    image = models.ImageField(
        upload_to="destinations/"
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):

        return f"{self.destination.name} Image"


# =========================================================
# DESTINATION PLACE
# =========================================================


from django.db import models
from django.conf import settings
from django.db.models import Avg
from datetime import datetime

class DestinationPlace(ApprovalMixin):

    # =====================================================
    # CHOICES
    # =====================================================

    DIFFICULTY_LEVELS = [
        ("easy", "Easy"),
        ("moderate", "Moderate"),
        ("hard", "Hard"),
    ]

    PERSON_TYPES = [
        ("family", "Family"),
        ("couples", "Couples"),
        ("solo", "Solo"),
        ("friends", "Friends"),
        ("adventure", "Adventure"),
        ("all", "All"),
    ]

    WEATHER_CHOICES = [
        ("sunny", "Sunny"),
        ("cold", "Cold"),
        ("rainy", "Rainy"),
        ("snow", "Snow"),
        ("cloudy", "Cloudy"),
    ]

    # =====================================================
    # RELATION
    # =====================================================

    destination = models.ForeignKey(
        Destination,
        on_delete=models.CASCADE,
        related_name="places"
    )

    # =====================================================
    # BASIC
    # =====================================================

    name = models.CharField(max_length=200)

    description = models.TextField()

    category = models.CharField(
        max_length=100,
        blank=True
    )

    is_hidden_gem = models.BooleanField(default=False)

    # =====================================================
    # LOCATION
    # =====================================================

    latitude = models.FloatField(
        blank=True,
        null=True
    )

    longitude = models.FloatField(
        blank=True,
        null=True
    )

    # =====================================================
    # WEATHER
    # =====================================================

    preferred_weather = models.CharField(
        max_length=50,
        choices=WEATHER_CHOICES,
        blank=True
    )

    weather_score = models.FloatField(default=10)

    seasonal_score = models.FloatField(default=10)

    rating_score = models.FloatField(default=0)

    # =====================================================
    # TRAVEL INFO
    # =====================================================

    how_to_reach = models.TextField(blank=True)

    # =====================================================
    # TIMINGS
    # =====================================================

    opening_time = models.TimeField(
        blank=True,
        null=True
    )

    closing_time = models.TimeField(
        blank=True,
        null=True
    )

    best_time_of_day = models.CharField(
        max_length=100,
        blank=True
    )

    best_months_to_visit = models.CharField(
        max_length=200,
        blank=True
    )

    avg_visit_duration = models.PositiveIntegerField(
        default=120
    )

    crowd_level = models.CharField(
        max_length=100,
        blank=True
    )

    # =====================================================
    # EXPERIENCE
    # =====================================================

    difficulty_level = models.CharField(
        max_length=20,
        choices=DIFFICULTY_LEVELS,
        default="easy"
    )

    suitable_for = models.CharField(
        max_length=50,
        choices=PERSON_TYPES,
        default="all"
    )

    best_for_photography = models.BooleanField(default=False)

    best_for_sunset = models.BooleanField(default=False)

    best_for_sunrise = models.BooleanField(default=False)

    # =====================================================
    # ACTIVITIES
    # =====================================================

    things_to_do = models.TextField(blank=True)

    # =====================================================
    # COST
    # =====================================================

    entry_fee = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0
    )

    parking_fee = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0
    )

    # =====================================================
    # TIPS
    # =====================================================

    travel_tips = models.TextField(blank=True)

    safety_tips = models.TextField(blank=True)

    things_to_carry = models.TextField(blank=True)

    # =====================================================
    # AI SCORING
    # =====================================================

    manual_priority_score = models.FloatField(default=10)

    popularity_score = models.FloatField(default=0)

    final_trending_score = models.FloatField(default=0)

    # =====================================================
    # STATS
    # =====================================================

    visit_count = models.PositiveIntegerField(default=0)

    total_reviews = models.PositiveIntegerField(default=0)

    average_rating = models.FloatField(default=0)

    # =====================================================
    # USER
    # =====================================================

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    # =====================================================
    # WEATHER SCORE
    # =====================================================

    def calculate_weather_score(self):

        score = 10

        weather = (
            getattr(self.destination, "weather_condition", "") or ""
        ).lower()

        preferred = (
            self.preferred_weather or ""
        ).lower()

        if preferred and preferred in weather:
            score += 10

        if "clear" in weather:
            score += 5

        if "storm" in weather:
            score -= 5

        return max(score, 0)

    # =====================================================
    # SEASON SCORE
    # =====================================================

    def calculate_season_score(self):

        current_month = datetime.now().strftime("%B").lower()

        best_months = (
            self.best_months_to_visit or ""
        ).lower()

        if current_month in best_months:
            return 20

        return 8

    # =====================================================
    # POPULARITY SCORE
    # =====================================================

    def calculate_popularity_score(self):

        score = 0

        score += self.average_rating * 4

        score += min(self.total_reviews * 0.25, 10)

        score += min(self.visit_count * 0.02, 10)

        if self.is_hidden_gem:
            score += 4

        if self.best_for_photography:
            score += 3

        if float(self.entry_fee) == 0:
            score += 3

        return round(min(score, 35), 2)

    # =====================================================
    # RATING SCORE
    # =====================================================

    def calculate_rating_score(self):

        return round(self.average_rating * 4, 2)

    # =====================================================
    # FINAL SCORE
    # =====================================================

    def update_scores(self):

        self.weather_score = self.calculate_weather_score()

        self.seasonal_score = self.calculate_season_score()

        self.popularity_score = self.calculate_popularity_score()

        self.rating_score = self.calculate_rating_score()

        self.final_trending_score = round(
            self.manual_priority_score +
            self.weather_score +
            self.seasonal_score +
            self.popularity_score +
            self.rating_score,
            2
        )

    # =====================================================
    # REFRESH REVIEW STATS
    # =====================================================

    def refresh_review_stats(self):

        self.total_reviews = self.reviews.count()

        self.average_rating = (
            self.reviews.aggregate(
                Avg("rating")
            )["rating__avg"] or 0
        )

        self.update_scores()

        self.save()

    # =====================================================
    # SAVE
    # =====================================================

    def save(self, *args, **kwargs):

        self.update_scores()

        super().save(*args, **kwargs)

    # =====================================================
    # STRING
    # =====================================================

    def __str__(self):

        return self.name



# =========================================================
# PLACE IMAGES
# =========================================================

class PlaceImage(models.Model):

    place = models.ForeignKey(
        DestinationPlace,
        on_delete=models.CASCADE,
        related_name="images"
    )

    image = models.ImageField(
        upload_to="places/"
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):

        return f"{self.place.name} Image"


# =========================================================
# PLACE ACTIVITIES
# =========================================================

class PlaceActivity(models.Model):

    place = models.ForeignKey(
        DestinationPlace,
        on_delete=models.CASCADE,
        related_name="activities"
    )

    name = models.CharField(
        max_length=200
    )

    description = models.TextField(
        blank=True
    )

    price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0
    )

    duration = models.CharField(
        max_length=100,
        blank=True
    )

    is_available = models.BooleanField(
        default=True
    )

    def __str__(self):

        return self.name


# =========================================================
# PLACE REVIEWS
# =========================================================

class PlaceReview(models.Model):

    RATING_CHOICES = [
        (1, "1"),
        (2, "2"),
        (3, "3"),
        (4, "4"),
        (5, "5"),
    ]

    place = models.ForeignKey(
        DestinationPlace,
        on_delete=models.CASCADE,
        related_name="reviews"
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    rating = models.IntegerField(
        choices=RATING_CHOICES
    )

    review = models.TextField()

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):

        return f"{self.place.name} - {self.rating}"
    

class DestinationReview(models.Model):
    destination = models.ForeignKey(
        Destination,
        on_delete=models.CASCADE,
        related_name="reviews"
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    rating = models.PositiveIntegerField()

    review = models.TextField()

    created_at = models.DateTimeField(
        auto_now_add=True
    )