# planner/forms.py

from django import forms
from .models import TripRequest


# =========================================================
# 🔥 TRIP FORM
# =========================================================

class TripForm(forms.ModelForm):

    class Meta:

        model = TripRequest

        fields = [
            # BASIC
            'destination',
            'starting_place',
            'ending_place',
            'days',
            'interests',
            
            # TRAVELER
            'traveler_name',
            'traveler_type',
            
            # BUDGET + HOTEL
            'budget',
            'hotel_type',
            'hotel_stars',
            
            # FOOD
            'food_preference',
            
            # ACTIVITY STYLE
            'activity_level',
            
            # DATE
            'start_date',
            
            # TRANSPORT
            'transport_mode',
            
            # EXPERIENCE OPTIONS
            'include_hidden_gems',
            'include_nightlife',
            'include_shopping',
            'include_local_food',
            
            # SPECIAL REQUIREMENTS
            'special_requirements',
        ]

        # =====================================================
        # 🔥 WIDGETS
        # =====================================================

        widgets = {

            # DESTINATION
            'destination': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Goa, Paris, Tokyo, Bali',
                'required': True
            }),
            
            # STARTING PLACE
            'starting_place': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Airport, Railway Station, Hotel',
                'required': False
            }),
            
            # ENDING PLACE
            'ending_place': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Airport, Railway Station, Hotel',
                'required': False
            }),
            
            # DAYS
            'days': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 30,
                'value': 3
            }),
            
            # INTERESTS
            'interests': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'e.g., beaches, nightlife, nature, trekking, museums, food',
                'required': True
            }),
            
            # TRAVELER NAME
            'traveler_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your name'
            }),
            
            # TRAVELER TYPE
            'traveler_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            
            # BUDGET
            'budget': forms.Select(attrs={
                'class': 'form-select'
            }),
            
            # HOTEL TYPE
            'hotel_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            
            # HOTEL STARS
            'hotel_stars': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 5,
                'value': 4
            }),
            
            # FOOD PREFERENCE
            'food_preference': forms.Select(attrs={
                'class': 'form-select'
            }),
            
            # ACTIVITY LEVEL
            'activity_level': forms.Select(attrs={
                'class': 'form-select'
            }),
            
            # START DATE
            'start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            
            # TRANSPORT MODE
            'transport_mode': forms.Select(attrs={
                'class': 'form-select'
            }),
            
            # CHECKBOXES
            'include_hidden_gems': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            
            'include_nightlife': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            
            'include_shopping': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            
            'include_local_food': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            
            # SPECIAL REQUIREMENTS
            'special_requirements': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'e.g., Wheelchair accessibility, honeymoon trip, photography spots, kids friendly, adventure focused'
            }),
        }

        # =====================================================
        # 🔥 HELP TEXTS
        # =====================================================

        help_texts = {
            'interests': 'Separate multiple interests with commas',
            'special_requirements': 'Optional custom AI instructions',
            'starting_place': 'Where will you start your journey?',
            'ending_place': 'Where will your trip end?',
        }

        # =====================================================
        # 🔥 LABELS
        # =====================================================

        labels = {
            'destination': '📍 Destination',
            'starting_place': '🚩 Starting Place (Optional)',
            'ending_place': '🏁 Ending Place (Optional)',
            'days': '📅 Trip Duration (Days)',
            'interests': '🎯 Travel Interests',
            'traveler_name': '👤 Traveler Name',
            'traveler_type': '👥 Traveler Type',
            'budget': '💰 Budget',
            'hotel_type': '🏨 Hotel Type',
            'hotel_stars': '⭐ Hotel Stars',
            'food_preference': '🍽️ Food Preference',
            'activity_level': '⚡ Travel Pace',
            'start_date': '📆 Start Date (Optional)',
            'transport_mode': '🚗 Transport Mode',
            'include_hidden_gems': '💎 Hidden Gems',
            'include_nightlife': '🌃 Nightlife',
            'include_shopping': '🛍️ Shopping',
            'include_local_food': '🍜 Local Food',
            'special_requirements': '📝 Special Requirements',
        }

    # =========================================================
    # 🔥 CUSTOM VALIDATION
    # =========================================================

    def clean_days(self):
        days = self.cleaned_data.get('days')
        if days < 1:
            raise forms.ValidationError("Trip must be at least 1 day.")
        if days > 30:
            raise forms.ValidationError("Maximum allowed trip is 30 days.")
        return days

    def clean_destination(self):
        destination = self.cleaned_data.get('destination')
        if not destination or len(destination.strip()) < 2:
            raise forms.ValidationError("Please enter a valid destination.")
        return destination.strip()
    
    def clean_interests(self):
        interests = self.cleaned_data.get('interests')
        if not interests or len(interests.strip()) < 3:
            raise forms.ValidationError("Please enter at least one interest.")
        return interests.strip()