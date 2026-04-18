from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta

class AgencyProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    agency_name = models.CharField(max_length=200)
    license_number = models.CharField(max_length=100)
    license_document = models.FileField(upload_to='agency/licenses/',null=True,blank=True)
    id_proof = models.FileField(upload_to='agency/idproofs/',null=True,blank=True)
    address = models.TextField()
    mobile = models.CharField(max_length=15)
    city=models.CharField(max_length=20)
    state=models.CharField(max_length=20)

    description = models.TextField(blank=True)
    experience_years = models.PositiveIntegerField(blank=True, null=True)
    tour_packages = models.BooleanField(default=False)
    flight_booking = models.BooleanField(default=False)
    cab_service = models.BooleanField(default=False)
    visa_service = models.BooleanField(default=False)
    travel_insurance = models.BooleanField(default=False)
    website = models.URLField(blank=True)
    instagram = models.URLField(blank=True)
    


    is_approved = models.BooleanField(default=False)



class TourPackage(models.Model):

    DIFFICULTY_LEVELS = [
        ('easy', 'Easy'),
        ('moderate', 'Moderate'),
        ('challenging', 'Challenging'),
        ('difficult', 'Difficult'),
    ]

    agency = models.ForeignKey(
        AgencyProfile,
        on_delete=models.CASCADE,
        related_name="packages"
    )

    title = models.CharField(max_length=200)
    description = models.TextField()

    duration_days = models.IntegerField()
    duration_nights = models.IntegerField()

    places_covered = models.CharField(max_length=300)

    # Group size
    min_group_size = models.PositiveIntegerField(default=1, null=True, blank=True)
    max_group_size = models.PositiveIntegerField(default=10, null=True, blank=True)

    guide_language = models.CharField(max_length=100)

    # Pricing
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discounted_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    # New fields for package details
    best_season = models.CharField(max_length=200, blank=True, null=True, 
                                   help_text="e.g., October to March, Summer Months, Throughout the year")
    difficulty_level = models.CharField(max_length=20, choices=DIFFICULTY_LEVELS, 
                                        default='moderate', blank=True, null=True)
    
    # Booking advance restrictions
    min_booking_days = models.PositiveIntegerField(default=1, blank=True, null=True,
                                                   help_text="Minimum days before travel to book this package")
    max_booking_days = models.PositiveIntegerField(default=365, blank=True, null=True,
                                                   help_text="Maximum days before travel to book this package")

    # Other fields
    pickup_points = models.TextField(blank=True, null=True)
    drop_points = models.TextField(blank=True, null=True)

    accommodation_type = models.CharField(max_length=100, blank=True, null=True)
    transport_type = models.CharField(max_length=100, blank=True, null=True)
    meals = models.CharField(max_length=100, blank=True, null=True)

    suitable_for = models.CharField(max_length=100, blank=True, null=True)
    things_to_carry = models.TextField(blank=True, null=True)

    inclusions = models.TextField(blank=True, null=True)
    exclusions = models.TextField(blank=True, null=True)

    cancellation_policy = models.TextField(blank=True, null=True)
    terms_conditions = models.TextField(blank=True, null=True)
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def discount_percentage(self):
        if self.discounted_price and self.discounted_price > 0:
            return int(round((self.price - self.discounted_price) / self.price * 100))
        return 0

    def __str__(self):
        return self.title
    
    def clean(self):
    # Validate booking days
        if self.min_booking_days and self.max_booking_days:
            if self.min_booking_days > self.max_booking_days:
                raise ValidationError({
                    'min_booking_days': 'Minimum booking days cannot be greater than maximum booking days.'
                })
    
    # Validate group size
        if self.min_group_size and self.max_group_size:
            if self.min_group_size > self.max_group_size:
                raise ValidationError({
                    'min_group_size': 'Minimum group size cannot be greater than maximum group size.'
                })
    
    # Validate price
        if self.discounted_price and self.discounted_price >= self.price:
            raise ValidationError({
                'discounted_price': 'Discounted price should be less than the original price.'
            })

    def save(self, *args, **kwargs):
        self.full_clean()  # This will call the clean method
        super().save(*args, **kwargs)

    def can_book_on_date(self, travel_date):
        """
        Check if a given travel date is within the booking window
        """
        if not travel_date:
            return False
        
        today = timezone.now().date()
        days_before_travel = (travel_date - today).days
        
        min_days = self.min_booking_days or 1
        max_days = self.max_booking_days or 365
        
        return min_days <= days_before_travel <= max_days
    
    def get_earliest_booking_date(self):
        """
        Get the earliest date from which this package can be booked
        """
        today = timezone.now().date()
        return today + timedelta(days=self.min_booking_days or 1)
    
    def get_latest_booking_date(self, travel_date):
        """
        Get the latest date by which this package must be booked for a given travel date
        """
        if not travel_date:
            return None
        return travel_date - timedelta(days=self.min_booking_days or 1)


class PackageItinerary(models.Model):

    package = models.ForeignKey(
        TourPackage,
        on_delete=models.CASCADE,
        related_name="itineraries"
    )

    day_number = models.IntegerField()

    title = models.CharField(max_length=200)
    description = models.TextField()

    

    def __str__(self):
        return f"{self.package.title} - Day {self.day_number}"
  

from django.utils.timezone import now


class PackageBooking(models.Model):

    package = models.ForeignKey(TourPackage, on_delete=models.CASCADE)

    traveller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    travellers_count = models.PositiveIntegerField()
    travel_date = models.DateField()
    booked_at = models.DateTimeField(auto_now_add=True)

    status = models.CharField(
    max_length=20,
    choices=[
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("rejected", "Rejected"),   # ✅ ADD THIS
        ("cancelled", "Cancelled")
    ],
    default="pending"
    )

    cancelled_by = models.CharField(
        max_length=20,
        choices=[
            ("user", "User"),
            ("agency", "Agency"),
            ("system", "System")
        ],
        null=True,
        blank=True
    )

    # 💳 PAYMENT
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    advance_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    remaining_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    payment_status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("partial", "Partial Paid"),
            ("paid", "Fully Paid")
        ],
        default="pending"
    )

    # ❌ NEW: who cancelled
    cancelled_by = models.CharField(
        max_length=20,
        choices=[
            ("user", "User"),
            ("agency", "Agency"),
            ("system", "System")
        ],
        null=True,
        blank=True
    )

    # 💸 store refund
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    refund_percentage = models.IntegerField(null=True, blank=True)

    # ===============================
    # ✅ REFUND PERCENTAGE
    # ===============================
    def get_refund_percentage(self):
        days_left = (self.travel_date - now().date()).days
        policies = self.package.cancellation_policies.all().order_by('-days_before')

        for policy in policies:
            if days_left >= policy.days_before:
                return policy.refund_percentage

        return 0

    # ===============================
    # ✅ FINAL REFUND
    # ===============================
    def calculate_refund_amount(self):
        total = self.total_amount or 0

        # 💥 FULL refund cases
        if self.cancelled_by in ["agency", "system"]:
            return total

        percentage = self.get_refund_percentage() or 0
        return (total * percentage) / 100
    

class PackageImage(models.Model):

    package = models.ForeignKey(
        TourPackage,
        on_delete=models.CASCADE,
        related_name="images"
    )

    image = models.ImageField(upload_to="tour_package/gallery/",
                              blank=True,
                              null=True)

    def __str__(self):
        return f"Image for {self.package.title}"
    

class Payment(models.Model):
        PAYMENT_TYPE = (
            ("advance", "Advance"),
            ("full", "Full Payment"),
        )

        booking = models.ForeignKey(PackageBooking, on_delete=models.CASCADE, related_name="payments")

        amount = models.DecimalField(max_digits=10, decimal_places=2)

        payment_type = models.CharField(max_length=10, choices=PAYMENT_TYPE)

        is_paid = models.BooleanField(default=False)

        transaction_id = models.CharField(max_length=200, blank=True, null=True)

        paid_at = models.DateTimeField(null=True, blank=True)


class CancellationPolicy(models.Model):
    package = models.ForeignKey(
        TourPackage,
        on_delete=models.CASCADE,
        related_name="cancellation_policies"
    )

    days_before = models.IntegerField()  
    refund_percentage = models.IntegerField()

    def __str__(self):
        return f"{self.days_before} days → {self.refund_percentage}% refund"