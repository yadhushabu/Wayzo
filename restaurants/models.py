from django.db import models
from django.conf import settings
from multiselectfield import MultiSelectField
from django.core.exceptions import ValidationError


class RestaurantProfile(models.Model):

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    # =========================
    # BASIC IDENTITY
    # =========================

    restaurant_name = models.CharField(max_length=200)

    property_type = models.CharField(
        max_length=50,
        choices=[
            ("Restaurant", "Restaurant"),
            ("Hotel", "Hotel"),
            ("Resort", "Resort"),
            ("Homestay", "Homestay"),
            ("Cafe", "Cafe")
        ]
    )

    description = models.TextField(blank=True)

    # =========================
    # VERIFICATION
    # =========================

    fssai_license_number = models.CharField(max_length=200)
    license_document = models.FileField(upload_to='licenses/')
    id_proof = models.FileField(upload_to='id_proofs/')
    is_approved = models.BooleanField(default=False)

    # =========================
    # LOCATION
    # =========================

    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    nearby_area = models.CharField(max_length=100, blank=True)

    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    mobile = models.CharField(max_length=20)

    website = models.URLField(blank=True)
    instagram = models.URLField(blank=True)

    # =========================
    # SERVICE FLAGS
    # =========================

    has_table_service = models.BooleanField(default=False)
    has_room_service = models.BooleanField(default=False)

    table_booking_enabled = models.BooleanField(default=False)
    room_booking_enabled = models.BooleanField(default=False)

    # Operating hours (same for all tables)
    opening_time = models.TimeField(null=True, blank=True)
    closing_time = models.TimeField(null=True, blank=True)
    
    # Food options (same for all tables)
    DIETARY_TYPE_CHOICES = [
        ("veg", "Veg"),
        ("non_veg", "Non Veg"),
        ("both", "Veg & Non Veg"),
    ]
    dietary_type = models.CharField(
        max_length=20,
        choices=DIETARY_TYPE_CHOICES,
        default="both"
    )
    
    cuisine_tags = models.CharField(
        max_length=200,
        blank=True,
        help_text="Comma separated (e.g. Kerala, Chinese, Italian)"
    )
    
    # Default slot duration for all tables
    default_slot_duration_minutes = models.IntegerField(default=90)
    default_max_prebooking_days = models.IntegerField(default=30)

    requires_table_advance = models.BooleanField(
        default=False
    )

    table_advance_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    avg_rating = models.FloatField(default=0.0, help_text="Average rating from customer reviews")
    
    # You might also want to add these optional fields:
    total_reviews = models.IntegerField(default=0, help_text="Total number of reviews")

    # =========================
    # STATUS
    # =========================

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.restaurant_name


class Table(models.Model):

    restaurant = models.ForeignKey(
        RestaurantProfile,
        on_delete=models.CASCADE,
        related_name="tables"
    )

    # =========================
    # BASIC TABLE INFO
    # =========================

    table_number = models.CharField(max_length=20)
    capacity = models.IntegerField(default=2)

    zone = models.CharField(
        max_length=50,
        blank=True,
        help_text="e.g. Indoor, Outdoor, Rooftop, VIP"
    )

    is_active = models.BooleanField(default=True)


    is_reservable = models.BooleanField(default=True)

    # =========================
    # TABLE TYPE
    # =========================

    TABLE_TYPE_CHOICES = [
        ("normal", "Normal"),
        ("family", "Family"),
        ("couple", "Couple"),
        ("vip", "VIP"),
        ("private", "Private"),
    ]

    table_type = models.CharField(
        max_length=20,
        choices=TABLE_TYPE_CHOICES,
        default="normal"
    )

    # =========================
    # TABLE FEATURES
    # =========================

    has_ac = models.BooleanField(default=False)
    has_music = models.BooleanField(default=False)
    has_view = models.BooleanField(default=False)
    smoking_allowed = models.BooleanField(default=False)


    # =========================
    # LAYOUT & POSITIONING
    # =========================
    
    pos_x = models.IntegerField(default=0, help_text="X coordinate on floor plan (0-1000)")
    pos_y = models.IntegerField(default=0, help_text="Y coordinate on floor plan (0-1000)")
    
    width = models.IntegerField(default=80, help_text="Table width in pixels")
    height = models.IntegerField(default=80, help_text="Table height in pixels")
    
    shape = models.CharField(
        max_length=20,
        choices=[
            ("circle", "Circle"),
            ("square", "Square"),
            ("rectangle", "Rectangle"),
            ("round", "Round"),
        ],
        default="square"
    )
    
    rotation = models.IntegerField(default=0, help_text="Rotation in degrees (0-360)")
    
    # Table section/area for filtering
    section_name = models.CharField(max_length=50, blank=True, help_text="e.g., Window, Bar, Garden, VIP Area")
    
    # Popularity tracking
    booking_count = models.IntegerField(default=0)
    average_rating = models.FloatField(default=0.0)

    def __str__(self):
        return f"{self.restaurant.restaurant_name} - Table {self.table_number}"


class TableSlot(models.Model):

    table = models.ForeignKey(
        Table,
        on_delete=models.CASCADE,
        related_name="slots"
    )

    date = models.DateField()

    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

    is_booked = models.BooleanField(default=False)

    max_capacity = models.IntegerField(default=1)

    def __str__(self):
        return f"{self.table} - {self.start_time}"
    

class TableBooking(models.Model):
    table = models.ForeignKey(Table, on_delete=models.CASCADE)
    
    payment_status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("paid", "Paid"),
            ("refunded", "Refunded"),
            ("failed", "Failed"),
        ],
        default="pending"
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

    guests = models.IntegerField()

    status = models.CharField(
        max_length=20,
        choices=[("pending","Pending"),("confirmed","Confirmed"),("cancelled","Cancelled"),("completed","Completed")],
        default="pending"
    )

    advance_paid = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
        )
    
    special_request = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True) 
    updated_at = models.DateTimeField(auto_now=True)


class RoomType(models.Model):
    restaurant = models.ForeignKey(RestaurantProfile, on_delete=models.CASCADE, related_name="room_types")

    name = models.CharField(max_length=100)

    variant = models.CharField(max_length=20, choices=[("ac","AC"), ("non_ac","Non AC")])

    price_per_night = models.DecimalField(max_digits=10, decimal_places=2)

    max_guests = models.IntegerField(default=2)

class CancellationPolicy(models.Model):

    POLICY_CHOICES = [
        ("free", "Free Cancellation"),
        ("standard", "Standard"),
        ("strict", "Strict"),
    ]

    room_type = models.OneToOneField(
        RoomType,
        on_delete=models.CASCADE,
        related_name="cancellation_policy"
    )

    policy_type = models.CharField(
        max_length=20,
        choices=POLICY_CHOICES,
        default="standard"
    )

    free_until_days = models.IntegerField(default=7)

    refund_percentage_after = models.IntegerField(default=30)

    refund_until_days = models.IntegerField(default=2)

    def __str__(self):
        return f"{self.room_type.name} - {self.policy_type}"





class RoomTypeDetail(models.Model):

    room_type = models.OneToOneField(
        RoomType,
        on_delete=models.CASCADE,
        related_name="detail"
    )

    # =========================
    # BASIC INFO
    # =========================

    size_sqft = models.IntegerField(null=True, blank=True)

    view = models.CharField(max_length=100, blank=True)  # City View, Sea View

    bed_type = models.CharField(max_length=100, blank=True)

    bathrooms = models.IntegerField(default=1)

    # =========================
    # DESCRIPTION
    # =========================

    about_room = models.TextField(blank=True)

    # =========================
    # AMENITIES (TEXT BASED)
    # =========================

    other_amenities = models.TextField(blank=True)

    # =========================
    # CORE BOOLEAN FEATURES
    # =========================

    wifi = models.BooleanField(default=False)

    smoking_allowed = models.BooleanField(default=False)

    couple_friendly = models.BooleanField(default=False)

    tv = models.BooleanField(default=False)

    bathroom = models.BooleanField(default=True)

    air_conditioning = models.BooleanField(default=False)

    mineral_water = models.BooleanField(default=False)

    laundry_service = models.BooleanField(default=False)

    housekeeping = models.BooleanField(default=False)

    in_room_dining = models.BooleanField(default=False)

    iron_ironing_board = models.BooleanField(default=False)

    room_service = models.BooleanField(default=False)

class Room(models.Model):
    room_type = models.ForeignKey(RoomType, on_delete=models.CASCADE, related_name="rooms")

    room_number = models.CharField(max_length=20)

    status = models.CharField(
        max_length=20,
        choices=[("available","Available"), ("occupied","Occupied"), ("maintenance","Maintenance")],
        default="available"
    )

class RoomBooking(models.Model):

    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
        related_name="bookings"
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    # =========================
    # STAY DATES
    # =========================

    check_in = models.DateField()
    check_out = models.DateField()

    nights = models.PositiveIntegerField(default=1)

    # =========================
    # GUEST INFO
    # =========================

    guests = models.PositiveIntegerField(default=1)

    adults = models.PositiveIntegerField(default=1)
    children = models.PositiveIntegerField(default=0)

    # =========================
    # PRICING (IMPORTANT FOR REAL SYSTEM)
    # =========================

    price_per_night = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )

    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    # =========================
    # STATUS
    # =========================

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("cancelled", "Cancelled"),
        ("completed", "Completed"),
    ]

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )

    payment_status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("paid", "Paid"),
            ("refunded", "Refunded"),
            ("failed", "Failed"),
        ],
        default="pending"
    )

    # =========================
    # SPECIAL REQUESTS
    # =========================

    special_request = models.TextField(blank=True)

    # =========================
    # TIMESTAMP
    # =========================

    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):

        overlap = RoomBooking.objects.filter(
            room=self.room,
            status="confirmed"
        ).exclude(
            id=self.id
        ).filter(
            check_in__lt=self.check_out,
            check_out__gt=self.check_in
        )

        if overlap.exists():
            raise ValidationError(
                "Room already booked for these dates."
            )

    def __str__(self):
        return f"{self.user} - {self.room.room_number}"

class PropertyMedia(models.Model):

    SECTION_CHOICES = [
        ("rooms", "Rooms"),
        ("dining", "Dining Area"),
        ("reception", "Reception"),
        ("parking", "Parking"),
        ("pool", "Pool"),
        ("entrance", "Entrance"),
        ("activities", "Activities"),
        ("bathroom", "Bathroom"),
        ("gym", "Gym"),
        ("spa", "Spa"),
        ("menu", "Menu"),
        ("other", "Other"),
    ]

    restaurant = models.ForeignKey(
        RestaurantProfile,
        on_delete=models.CASCADE,
        related_name="media"
    )

    room_type = models.ForeignKey(
        RoomType,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="images"
    )

    section = models.CharField(max_length=30, choices=SECTION_CHOICES)

    title = models.CharField(max_length=100, blank=True)

    image = models.ImageField(upload_to="property_media/")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.restaurant.restaurant_name} - {self.section}"
    

class Review(models.Model):
    """Review model for restaurants/hotels - Direct posting, no admin approval"""
    
    restaurant = models.ForeignKey(
        RestaurantProfile,
        on_delete=models.CASCADE,
        related_name="reviews"
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="restaurant_reviews"
    )
    
    # Booking reference (to verify they actually visited)
    table_booking = models.ForeignKey(
        TableBooking,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviews"
    )
    
    room_booking = models.ForeignKey(
        RoomBooking,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviews"
    )
    
    # Review content
    rating = models.IntegerField(
        choices=[(i, i) for i in range(1, 6)],
        help_text="Rating from 1 to 5 stars"
    )
    
    title = models.CharField(max_length=200, blank=True)
    comment = models.TextField()
    
    # Separate ratings for different aspects (optional)
    food_rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)], null=True, blank=True)
    service_rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)], null=True, blank=True)
    ambiance_rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)], null=True, blank=True)
    value_rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)], null=True, blank=True)
    
    # Images (multiple images support)
    image1 = models.ImageField(upload_to='review_images/', null=True, blank=True)
    image2 = models.ImageField(upload_to='review_images/', null=True, blank=True)
    image3 = models.ImageField(upload_to='review_images/', null=True, blank=True)
    
    # Status - Verified based on booking, no admin approval needed
    is_verified = models.BooleanField(default=False, help_text="Verified purchase/visit")
    
    # Helpful votes (for community moderation)
    helpful_count = models.IntegerField(default=0)
    report_count = models.IntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['user', 'restaurant']  # One review per user per restaurant
    
    def __str__(self):
        return f"{self.user.username} - {self.restaurant.restaurant_name} - {self.rating}★"
    
    def can_review(self):
        """Check if user can review based on completed bookings"""
        from django.utils import timezone
        
        # Check table booking completed
        if self.table_booking and self.table_booking.status == 'completed':
            return True
        
        # Check room booking completed
        if self.room_booking and self.room_booking.status == 'completed':
            return True
        
        # Check if check-out date has passed for room booking
        if self.room_booking and self.room_booking.check_out:
            if self.room_booking.check_out <= timezone.now().date():
                return True
        
        return False

class Payment(models.Model):

    PAYMENT_TYPES = [
        ("room", "Room"),
        ("table", "Table"),
        ("package", "Package"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("success", "Success"),
        ("failed", "Failed"),
        ("refunded", "Refunded"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    room_booking = models.ForeignKey(
        RoomBooking,
        null=True,
        blank=True,
        on_delete=models.CASCADE
    )

    table_booking = models.ForeignKey(
        TableBooking,
        null=True,
        blank=True,
        on_delete=models.CASCADE
    )

    payment_type = models.CharField(
        max_length=20,
        choices=PAYMENT_TYPES
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    transaction_id = models.CharField(
        max_length=200,
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )

    refund_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    created_at = models.DateTimeField(auto_now_add=True)