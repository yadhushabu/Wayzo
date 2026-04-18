from django import forms

from agencies.models import CancellationPolicy, TourPackage
from .models import PropertyBooking, TravelPlan, TravellerProfile, ProfilePost

class TravellerProfileEditForm(forms.ModelForm):

    class Meta:
        model = TravellerProfile
        fields = [
            "first_name",
            "last_name",
            "mobile",
            "age",
            "gender",
            "address",
            "city",
            "state",
            "profile_picture",  
        ]


class NewPostForm(forms.ModelForm):
    class Meta:
        model = ProfilePost
        fields = ['caption', 'image', 'location']



from django import forms

class PropertyBookingForm(forms.ModelForm):
    class Meta:
        model = PropertyBooking
        fields = [
            "booking_type",
            "booking_date",
            "time",
            "guests",
            "check_in",
            "check_out",
            "rooms",
            "special_request"
        ]
        exclude = ['user', 'property', 'booking_type']
        widgets = {
    'check_in': forms.DateInput(attrs={'type': 'date'}),
    'check_out': forms.DateInput(attrs={'type': 'date'}),
}
        

from django import forms

from django import forms
from django import forms
from .models import TripPlan

class TripPlanForm(forms.ModelForm):  # ✅ Changed to ModelForm
    
    class Meta:
        model = TripPlan
        fields = [
            'destination', 'start_date', 'end_date', 'adults', 'children',
            'budget', 'interests', 'stay_type', 'room_type', 'amenities',
            'food_type', 'cuisines', 'travel_style', 'transport', 
            'trip_type', 'special_requests'
        ]
        widgets = {
            'start_date': forms.DateInput(attrs={
                'type': 'date', 
                'class': 'form-control',
                'placeholder': 'When do you want to start?'
            }),
            'end_date': forms.DateInput(attrs={
                'type': 'date', 
                'class': 'form-control',
                'placeholder': 'When do you want to end?'
            }),
            'special_requests': forms.Textarea(attrs={
                'rows': 4,
                'class': 'form-control',
                'placeholder': 'Any special needs? Kids activities? Anniversary? Dietary restrictions?'
            }),
            'interests': forms.CheckboxSelectMultiple(attrs={
                'class': 'form-check-input'
            }),
            'amenities': forms.CheckboxSelectMultiple(attrs={
                'class': 'form-check-input'
            }),
            'cuisines': forms.CheckboxSelectMultiple(attrs={
                'class': 'form-check-input'
            }),
        }
    
    # 🌟 CUSTOM VALIDATION
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError("End date must be after start date!")
        
        if start_date and end_date:
            days = (end_date - start_date).days + 1
            if days > 30:
                raise forms.ValidationError("Max 30-day trips supported!")
        
        return cleaned_data

# ✅ HELPER CHOICES (add to forms.py top)
BUDGET_CHOICES = [
    ("low", "💰 Low (< $50/day)"),
    ("medium", "💳 Medium ($50-150/day)"),
    ("luxury", "💎 Luxury (>$150/day)")
]

TRIP_TYPE_CHOICES = [
    ("family", "👨‍👩‍👧 Family"),
    ("couple", "💑 Couple/Romance"),
    ("friends", "👯 Friends"),
    ("solo", "🌍 Solo Adventure"),
    ("business", "💼 Business + Leisure")
]

STAY_TYPE_CHOICES = [
    ("hotel", "🏨 Hotel"),
    ("resort", "🏝️ Resort"),
    ("homestay", "🏠 Homestay"),
    ("villa", "🏰 Villa"),
    ("apartment", "🏢 Apartment"),
    ("any", "🤷 Any")
]

# ✅ Update your model choices to use these



from django import forms
from .models import TravelPlan


# travellers/forms.py
from django import forms
from .models import TravelPlan
from destinations.models import Destination

class TravelPlanForm(forms.ModelForm):
    
    # Use ModelChoiceField for destination
    destination = forms.ModelChoiceField(
        queryset=Destination.objects.all().order_by('name'),
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label="-- Select a destination --",
        required=True
    )
    
    class Meta:
        model = TravelPlan
        fields = [
            'destination',
            'travel_type',
            'mood',
            'adults',
            'children',
            'budget_range',
            'daily_budget',
            'number_of_days',
            'start_date',
            'start_time',
            'end_time',
            'transport_mode',
            'pace',
            'stay_type',
            'room_type',
            'food_preference',
            'cuisine_preference',
            'meal_budget',
            'activity_types',
            'must_visit_places',
            'max_travel_distance_per_day',
            'avoid_long_travel',
            'has_elderly',
            'needs_accessibility',
            'prefer_indoor',
            'rain_flexible',
            'nightlife_preference',
            'crowd_preference',
            'start_location_name',
            'start_latitude',
            'start_longitude',
            'end_location_name',
            'end_latitude',
            'end_longitude',
            'auto_book_stays',
            'auto_book_restaurants',
        ]
        
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'start_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'end_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'travel_type': forms.Select(attrs={'class': 'form-control'}),
            'mood': forms.Select(attrs={'class': 'form-control'}),
            'budget_range': forms.Select(attrs={'class': 'form-control'}),
            'transport_mode': forms.Select(attrs={'class': 'form-control'}),
            'pace': forms.Select(attrs={'class': 'form-control'}),
            'stay_type': forms.Select(attrs={'class': 'form-control'}),
            'room_type': forms.Select(attrs={'class': 'form-control'}),
            'food_preference': forms.Select(attrs={'class': 'form-control'}),
            'cuisine_preference': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Indian, Chinese, Italian'}),
            'meal_budget': forms.Select(attrs={'class': 'form-control'}),
            'activity_types': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., sightseeing, trekking, beach'}),
            'must_visit_places': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'List specific places you want to visit'}),
            'max_travel_distance_per_day': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 100'}),
            'crowd_preference': forms.Select(attrs={'class': 'form-control'}),
            'start_location_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Search or click on map'}),
            'end_location_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Search or click on map'}),
            
            # Checkboxes
            'avoid_long_travel': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_elderly': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'needs_accessibility': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'prefer_indoor': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'rain_flexible': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'nightlife_preference': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'auto_book_stays': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'auto_book_restaurants': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            
            # Hidden fields
            'start_latitude': forms.HiddenInput(),
            'start_longitude': forms.HiddenInput(),
            'end_latitude': forms.HiddenInput(),
            'end_longitude': forms.HiddenInput(),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make required fields obvious
        self.fields['destination'].required = True
        self.fields['travel_type'].required = True
        self.fields['mood'].required = True
        self.fields['number_of_days'].required = True