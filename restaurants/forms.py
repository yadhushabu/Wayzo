from django import forms
from .models import RestaurantProfile, Review, TableBooking, TableSlot


class RestaurantProfileForm(forms.ModelForm):

    class Meta:
        model = RestaurantProfile

        fields = [
            # =========================
            # DESCRIPTION
            # =========================
            "description",

            # =========================
            # LOCATION EXTRA
            # =========================
            "nearby_area",
            "latitude",
            "longitude",

            # =========================
            # SOCIAL
            # =========================
            "website",
            "instagram",

            # =========================
            # SERVICE FLAGS
            # =========================
            "has_table_service",
            "has_room_service",
            "table_booking_enabled",
            "room_booking_enabled",

            "requires_table_advance",
            "table_advance_amount",

             "opening_time",
            "closing_time",
            "dietary_type",
            "cuisine_tags",
            "default_slot_duration_minutes",
            "default_max_prebooking_days",
        ]

        widgets = {

            "description": forms.Textarea(
                attrs={
                    "rows": 4,
                    "class": "form-control",
                    "placeholder": "Write about your property..."
                }
            ),

            "nearby_area": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Nearby landmark / area"
                }
            ),

            "latitude": forms.NumberInput(
                attrs={
                    "step": "any",
                    "class": "form-control"
                }
            ),

            "longitude": forms.NumberInput(
                attrs={
                    "step": "any",
                    "class": "form-control"
                }
            ),

            "website": forms.URLInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "https://example.com"
                }
            ),

            "instagram": forms.URLInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Instagram link"
                }
            ),
            "opening_time": forms.TimeInput(attrs={"type": "time", "class": "form-control"}),
            "closing_time": forms.TimeInput(attrs={"type": "time", "class": "form-control"}),
            "cuisine_tags": forms.TextInput(attrs={"class": "form-control", "placeholder": "Kerala, Chinese, Italian"}),
            "default_slot_duration_minutes": forms.NumberInput(attrs={"class": "form-control", "min": 15}),
            "default_max_prebooking_days": forms.NumberInput(attrs={"class": "form-control", "min": 0}),

            "has_table_service": forms.CheckboxInput(),
            "has_room_service": forms.CheckboxInput(),
            "table_booking_enabled": forms.CheckboxInput(),
            "room_booking_enabled": forms.CheckboxInput(),
            "requires_table_advance": forms.CheckboxInput(),

            "table_advance_amount": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 0,
                    "step": "0.01",
                    "placeholder": "Advance amount"
                }
            ),
        }

        labels = {
            "opening_time": "Default Opening Time (All Tables)",
            "closing_time": "Default Closing Time (All Tables)",
            "dietary_type": "Default Dietary Type (All Tables)",
            "cuisine_tags": "Default Cuisine Tags (All Tables)",
            "default_slot_duration_minutes": "Default Slot Duration (minutes)",
            "default_max_prebooking_days": "Default Max Prebooking Days",
            "default_table_capacity": "Default Table Capacity",
            "default_table_type": "Default Table Type",
            "requires_table_advance": "Require Advance Payment",

            "table_advance_amount": "Advance Amount (₹)",
        }
    
    def clean(self):
        cleaned_data = super().clean()
        
        opening = cleaned_data.get("opening_time")
        closing = cleaned_data.get("closing_time")
        slot_duration = cleaned_data.get(
            "default_slot_duration_minutes"
        )

        requires_advance = cleaned_data.get(
            "requires_table_advance"
        )

        advance_amount = cleaned_data.get(
            "table_advance_amount"
        )
                
        # Time validation
        if opening and closing:
            if opening >= closing:
                self.add_error("closing_time", "Closing time must be after opening time.")
        
        # Slot duration validation
        if slot_duration and slot_duration < 15:
            self.add_error(
                "default_slot_duration_minutes",
                "Slot duration must be at least 15 minutes."
            )

        if requires_advance and advance_amount <= 0:
            self.add_error(
                "table_advance_amount",
                "Please enter an advance amount."
            )
        
        return cleaned_data


# restaurants/forms.py

from django import forms
from .models import (
    Table, RoomType, RoomTypeDetail, RoomBooking, 
    Room, PropertyMedia
)


# restaurants/forms.py - Update the TableForm

class TableForm(forms.ModelForm):
    """Form for Table model"""
    
    class Meta:
        model = Table
        fields = [
            "table_number",
            "capacity",
            "zone",
            "is_active",
            "is_reservable",
            "table_type",
            "has_ac",
            "has_music",
            "has_view",
            "smoking_allowed",
        ]
        
        widgets = {
            "table_number": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g., T1, Table 1"}),
            "capacity": forms.NumberInput(attrs={"class": "form-control", "min": 1, "value": 2}),
            "zone": forms.TextInput(attrs={"class": "form-control", "placeholder": "Indoor, Outdoor, VIP"}),
        }


class RoomTypeForm(forms.ModelForm):
    """Form for RoomType model"""
    
    class Meta:
        model = RoomType
        fields = [
            "name",
            "variant",
            "price_per_night",
            "max_guests",
        ]
        
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "variant": forms.Select(attrs={"class": "form-control"}),
            "price_per_night": forms.NumberInput(attrs={"class": "form-control", "min": 0, "step": 0.01}),
            "max_guests": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
        }
    
    def clean_price_per_night(self):
        price = self.cleaned_data.get("price_per_night")
        if price and price <= 0:
            raise forms.ValidationError("Price per night must be greater than 0.")
        return price
    
    def clean_max_guests(self):
        max_guests = self.cleaned_data.get("max_guests")
        if max_guests and max_guests <= 0:
            raise forms.ValidationError("Max guests must be greater than 0.")
        return max_guests


class RoomTypeDetailForm(forms.ModelForm):
    """Form for RoomTypeDetail model"""
    
    class Meta:
        model = RoomTypeDetail
        fields = [
            # BASIC INFO
            "size_sqft",
            "view",
            "bed_type",
            "bathrooms",
            
            # DESCRIPTION + POLICY
            "about_room",
            
            # AMENITIES TEXT
            "other_amenities",
            
            # BOOLEAN FEATURES
            "wifi",
            "smoking_allowed",
            "couple_friendly",
            "tv",
            "bathroom",
            "air_conditioning",
            "mineral_water",
            "laundry_service",
            "housekeeping",
            "in_room_dining",
            "iron_ironing_board",
            "room_service",
        ]
        
        widgets = {
            "size_sqft": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "view": forms.TextInput(attrs={"class": "form-control"}),
            "bed_type": forms.TextInput(attrs={"class": "form-control"}),
            "bathrooms": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "about_room": forms.Textarea(attrs={"rows": 4, "class": "form-control"}),
            "other_amenities": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
        }
    
    def clean_bathrooms(self):
        bathrooms = self.cleaned_data.get("bathrooms")
        if bathrooms and bathrooms < 0:
            raise forms.ValidationError("Number of bathrooms cannot be negative.")
        return bathrooms


class RoomForm(forms.ModelForm):
    """Form for Room model"""
    
    class Meta:
        model = Room
        fields = [
            "room_type",
            "room_number",
            "status",
        ]
        
        widgets = {
            "room_type": forms.Select(attrs={"class": "form-control"}),
            "room_number": forms.TextInput(attrs={"class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-control"}),
        }


class RoomBookingForm(forms.ModelForm):
    """Form for RoomBooking model"""
    
    class Meta:
        model = RoomBooking
        fields = [
            "check_in",
            "check_out",
            "guests",
            "adults",
            "children",
            "special_request",
        ]
        
        widgets = {
            "check_in": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "check_out": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "guests": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "adults": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "children": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "special_request": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        
        check_in = cleaned_data.get("check_in")
        check_out = cleaned_data.get("check_out")
        guests = cleaned_data.get("guests")
        adults = cleaned_data.get("adults")
        children = cleaned_data.get("children")
        
        # Date validation
        if check_in and check_out:
            if check_out <= check_in:
                self.add_error("check_out", "Check-out must be after check-in.")
        
        # Guest validation
        if guests and guests <= 0:
            self.add_error("guests", "Guests must be greater than 0.")
        
        if adults and adults <= 0:
            self.add_error("adults", "At least 1 adult is required.")
        
        if adults is not None and children is not None:
            total_guests = adults + children
            if guests and total_guests != guests:
                self.add_error("guests", f"Total guests (adults + children) should be {total_guests}")
        
        # Calculate nights if check_in and check_out are valid
        if check_in and check_out and check_out > check_in:
            nights = (check_out - check_in).days
            cleaned_data["nights"] = nights
        
        return cleaned_data


# restaurants/forms.py - Update PropertyMediaForm

class PropertyMediaForm(forms.ModelForm):
    """Form for PropertyMedia model - Single file upload"""
    
    class Meta:
        model = PropertyMedia
        fields = [
            "restaurant",
            "room_type",
            "section",
            "title",
            "image",
        ]
        
        widgets = {
            "restaurant": forms.Select(attrs={"class": "form-control"}),
            "room_type": forms.Select(attrs={"class": "form-control"}),
            "section": forms.Select(attrs={"class": "form-control"}),
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "image": forms.FileInput(attrs={"class": "form-control"}),
        }
    
    def clean_image(self):
        image = self.cleaned_data.get("image")
        if image:
            # Validate file size (max 5MB)
            if image.size > 5 * 1024 * 1024:
                raise forms.ValidationError("Image file size must be less than 5MB.")
            
            # Validate file extension
            valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
            import os
            ext = os.path.splitext(image.name)[1].lower()
            if ext not in valid_extensions:
                raise forms.ValidationError(f"Only {', '.join(valid_extensions)} formats are allowed.")
        
        return image

# Optional: Formset for bulk operations
from django.forms import inlineformset_factory

# Formset for RoomType and RoomTypeDetail
RoomTypeDetailFormSet = inlineformset_factory(
    RoomType,
    RoomTypeDetail,
    form=RoomTypeDetailForm,
    fields=RoomTypeDetailForm.Meta.fields,
    extra=1,
    can_delete=True
)

# Formset for RoomType and Room
RoomFormSet = inlineformset_factory(
    RoomType,
    Room,
    form=RoomForm,
    fields=["room_number", "status"],
    extra=1,
    can_delete=True
)

# Formset for Table slots (if needed)
TableSlotFormSet = inlineformset_factory(
    Table,
    TableSlot,
    fields=["date", "start_time", "end_time", "max_capacity"],
    extra=7,  # One week of slots
    can_delete=True
)

class TableBookingForm(forms.ModelForm):
    """Form for TableBooking model"""
    
    class Meta:
        model = TableBooking
        fields = [
            "table",
            "user",  # You might want to auto-populate this from request.user
            "start_time",
            "end_time",
            "guests",
            "status",
        ]
        
        widgets = {
            "table": forms.Select(attrs={"class": "form-control"}),
            "user": forms.Select(attrs={"class": "form-control"}),
            "start_time": forms.DateTimeInput(attrs={"type": "datetime-local", "class": "form-control"}),
            "end_time": forms.DateTimeInput(attrs={"type": "datetime-local", "class": "form-control"}),
            "guests": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "status": forms.Select(attrs={"class": "form-control"}),
        }
    
    def __init__(self, *args, **kwargs):
        # Optional: Populate user field with only active users
        # Or hide user field and auto-assign
        super().__init__(*args, **kwargs)
        
        # If you want to limit table choices to active/reservable tables only
        self.fields["table"].queryset = Table.objects.filter(
            is_active=True, 
            is_reservable=True
        )
        
        # Make user field optional if you're auto-assigning
        # self.fields["user"].required = False
    
    def clean(self):
        cleaned_data = super().clean()
        
        table = cleaned_data.get("table")
        start_time = cleaned_data.get("start_time")
        end_time = cleaned_data.get("end_time")
        guests = cleaned_data.get("guests")
        
        # Time validation
        if start_time and end_time:
            if end_time <= start_time:
                self.add_error("end_time", "End time must be after start time.")
        
        # Check if booking is within table operating hours
        if table and start_time:
            if table.opening_time and table.closing_time:
                booking_time = start_time.time()
                
                # Handle cases where closing time is past midnight
                if table.closing_time <= table.opening_time:
                    # Closing time is next day
                    pass
                else:
                    if booking_time < table.opening_time or booking_time > table.closing_time:
                        self.add_error(
                            "start_time", 
                            f"Booking time must be between {table.opening_time} and {table.closing_time}."
                        )
        
        # Capacity validation
        if table and guests:
            if guests > table.capacity:
                self.add_error(
                    "guests", 
                    f"Number of guests ({guests}) exceeds table capacity ({table.capacity})."
                )
            elif guests <= 0:
                self.add_error("guests", "Number of guests must be greater than 0.")
        
        # Check for overlapping bookings on the same table
        if table and start_time and end_time and not self.instance.pk:  # Skip for existing booking updates
            overlapping_bookings = TableBooking.objects.filter(
                table=table,
                status__in=["pending", "confirmed"],  # Only check active bookings
                start_time__lt=end_time,
                end_time__gt=start_time
            ).exclude(pk=self.instance.pk if self.instance else None)
            
            if overlapping_bookings.exists():
                self.add_error(
                    None,  # Non-field error
                    f"Table {table.table_number} is already booked for this time slot."
                )
        
        return cleaned_data
    

class ReviewForm(forms.ModelForm):
    """Form for leaving a review - Direct submission"""
    
    class Meta:
        model = Review
        fields = [
            'rating', 'title', 'comment',
            'food_rating', 'service_rating', 'ambiance_rating', 'value_rating',
            'image1', 'image2', 'image3'
        ]
        widgets = {
            'rating': forms.Select(attrs={'class': 'form-control', 'required': True}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Summarize your experience (optional)'}),
            'comment': forms.Textarea(attrs={'rows': 5, 'class': 'form-control', 'placeholder': 'Share your experience in detail...', 'required': True}),
            'food_rating': forms.Select(attrs={'class': 'form-control'}),
            'service_rating': forms.Select(attrs={'class': 'form-control'}),
            'ambiance_rating': forms.Select(attrs={'class': 'form-control'}),
            'value_rating': forms.Select(attrs={'class': 'form-control'}),
            'image1': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'image2': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'image3': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }
        labels = {
            'rating': 'Overall Rating *',
            'title': 'Review Title (Optional)',
            'comment': 'Your Review *',
            'food_rating': 'Food Quality',
            'service_rating': 'Service Quality',
            'ambiance_rating': 'Ambiance',
            'value_rating': 'Value for Money',
            'image1': 'Photo 1 (Optional)',
            'image2': 'Photo 2 (Optional)',
            'image3': 'Photo 3 (Optional)',
        }
