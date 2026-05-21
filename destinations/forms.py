from django import forms
from django.core.validators import MinValueValidator, MaxValueValidator
from .models import (
    Destination, DestinationImage, DestinationPlace, 
    PlaceImage, PlaceActivity, PlaceReview
)

from django import forms
from .models import Destination


class DestinationForm(forms.ModelForm):

    # =========================
    # UX: Month range input
    # =========================

    best_month_start = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=12,
        widget=forms.NumberInput(attrs={
            "class": "form-control",
            "placeholder": "Start month (1-12)"
        })
    )

    best_month_end = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=12,
        widget=forms.NumberInput(attrs={
            "class": "form-control",
            "placeholder": "End month (1-12)"
        })
    )

    latitude = forms.FloatField(
        required=False,
        widget=forms.NumberInput(attrs={
            "step": "any",
            "class": "form-control"
        })
    )

    longitude = forms.FloatField(
        required=False,
        widget=forms.NumberInput(attrs={
            "step": "any",
            "class": "form-control"
        })
    )

    class Meta:
        model = Destination
        fields = [
            "name",
            "description",
            "country",
            "state",
            "city",
            "latitude",
            "longitude",
            "best_season",
            "best_month_start",
            "best_month_end",
            "preferred_weather",
            "is_featured",
        ]

        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "country": forms.TextInput(attrs={"class": "form-control"}),
            "state": forms.TextInput(attrs={"class": "form-control"}),
            "city": forms.TextInput(attrs={"class": "form-control"}),

            "best_season": forms.Select(attrs={"class": "form-control"}),

            "preferred_weather": forms.Select(attrs={"class": "form-control"}),

            "is_featured": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

        help_texts = {
            'name': 'Full name of the destination (must be unique)',
            'country': 'Country where the destination is located',
            'city': 'City or major town',
            'state': 'State or province (optional)',
            'latitude': 'Auto-fetched from map or enter manually',
            'longitude': 'Auto-fetched from map or enter manually',
            'best_season': 'Best time of year to visit (e.g., Spring, Summer)',
            'is_featured': 'Mark as featured destination (staff only)',
        }
    
    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name:
            name = ' '.join(name.split())
            if len(name) < 3:
                raise forms.ValidationError("Destination name must be at least 3 characters long.")
            
            instance = self.instance
            if Destination.objects.filter(name__iexact=name).exclude(pk=instance.pk).exists():
                raise forms.ValidationError("A destination with this name already exists.")
        return name
    
    def clean_country(self):
        country = self.cleaned_data.get('country')
        if country:
            country = ' '.join(country.split())
            if len(country) < 2:
                raise forms.ValidationError("Please enter a valid country name.")
        return country
    
    def clean_latitude(self):
        latitude = self.cleaned_data.get('latitude')
        if latitude:
            if latitude < -90 or latitude > 90:
                raise forms.ValidationError("Latitude must be between -90 and 90 degrees.")
        return latitude
    
    def clean_longitude(self):
        longitude = self.cleaned_data.get('longitude')
        if longitude:
            if longitude < -180 or longitude > 180:
                raise forms.ValidationError("Longitude must be between -180 and 180 degrees.")
        return longitude
    
    def clean(self):
        cleaned_data = super().clean()
        latitude = cleaned_data.get('latitude')
        longitude = cleaned_data.get('longitude')
        
        if (latitude and not longitude) or (longitude and not latitude):
            raise forms.ValidationError("Both latitude and longitude are required if providing coordinates.")
        
        return cleaned_data


class DestinationImageForm(forms.ModelForm):
    """Form for uploading destination images"""
    
    class Meta:
        model = DestinationImage
        fields = ['image']
        widgets = {
            'image': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            })
        }
    
    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image:
            # Check file size (max 10MB)
            if image.size > 10 * 1024 * 1024:
                raise forms.ValidationError("Image file size cannot exceed 10MB.")
            
            # Check file extension
            valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
            if not any(image.name.lower().endswith(ext) for ext in valid_extensions):
                raise forms.ValidationError("Only JPG, JPEG, PNG, GIF, and WEBP files are allowed.")
        
        return image


# forms.py
class DestinationPlaceForm(forms.ModelForm):
    class Meta:
        model = DestinationPlace
        fields = [
            'name', 'description', 'category', 'latitude', 'longitude',
            'opening_time', 'closing_time', 'entry_fee', 'parking_fee',
            'avg_visit_duration', 'best_time_of_day', 'best_months_to_visit',
            'difficulty_level', 'suitable_for', 'best_for_photography',
            'best_for_sunset', 'best_for_sunrise', 'how_to_reach', 'things_to_do',
            'travel_tips', 'safety_tips', 'things_to_carry', 'preferred_weather',
            'priority_score', 'is_hidden_gem'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'latitude': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any'}),
            'longitude': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any'}),
            'opening_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'closing_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'entry_fee': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'parking_fee': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'avg_visit_duration': forms.NumberInput(attrs={'class': 'form-control'}),
            'best_time_of_day': forms.Select(attrs={'class': 'form-control'}),
            'best_months_to_visit': forms.TextInput(attrs={'class': 'form-control'}),
            'difficulty_level': forms.Select(attrs={'class': 'form-control'}),
            'suitable_for': forms.Select(attrs={'class': 'form-control'}),
            'best_for_photography': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'best_for_sunset': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'best_for_sunrise': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'how_to_reach': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'things_to_do': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'travel_tips': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'safety_tips': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'things_to_carry': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'preferred_weather': forms.Select(attrs={'class': 'form-control'}),
            'priority_score': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100}),
            'is_hidden_gem': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        
        help_texts = {
            'avg_visit_duration': 'Time in minutes (e.g., 120 for 2 hours)',
            'entry_fee': 'Entry fee in local currency',
            'parking_fee': 'Parking fee if applicable',
            'is_hidden_gem': 'Check if this is an offbeat/less-known location',
            'best_for_photography': 'Good for photography',
            'best_for_sunset': 'Famous for sunset views',
            'best_for_sunrise': 'Famous for sunrise views',
        }
    
    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name:
            name = ' '.join(name.split())
            if len(name) < 3:
                raise forms.ValidationError("Place name must be at least 3 characters long.")
        return name
    
    def clean_avg_visit_duration(self):
        duration = self.cleaned_data.get('avg_visit_duration')
        if duration and duration < 0:
            raise forms.ValidationError("Duration cannot be negative.")
        if duration and duration > 1440:  # 24 hours max
            raise forms.ValidationError("Duration cannot exceed 24 hours (1440 minutes).")
        return duration
    
    def clean_entry_fee(self):
        fee = self.cleaned_data.get('entry_fee')
        if fee and fee < 0:
            raise forms.ValidationError("Entry fee cannot be negative.")
        return fee
    
    def clean_parking_fee(self):
        fee = self.cleaned_data.get('parking_fee')
        if fee and fee < 0:
            raise forms.ValidationError("Parking fee cannot be negative.")
        return fee
    
    def clean(self):
        cleaned_data = super().clean()
        opening = cleaned_data.get('opening_time')
        closing = cleaned_data.get('closing_time')
        
        if opening and closing and opening >= closing:
            raise forms.ValidationError("Closing time must be after opening time.")
        
        return cleaned_data


class PlaceImageForm(forms.ModelForm):
    """Form for uploading place images"""
    
    class Meta:
        model = PlaceImage
        fields = ['image']
        widgets = {
            'image': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            })
        }
    
    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image:
            if image.size > 10 * 1024 * 1024:
                raise forms.ValidationError("Image file size cannot exceed 10MB.")
            
            valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
            if not any(image.name.lower().endswith(ext) for ext in valid_extensions):
                raise forms.ValidationError("Only JPG, JPEG, PNG, GIF, and WEBP files are allowed.")
        
        return image


class PlaceActivityForm(forms.ModelForm):
    """Form for creating/updating activities at a place"""
    
    price = forms.DecimalField(
        max_digits=8,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'placeholder': '0.00'
        })
    )
    
    class Meta:
        model = PlaceActivity
        fields = [
            "name",
            "description",
            "price",
            "duration",
            "is_available"
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Guided Tour'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe the activity...'
            }),
            'duration': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., 2 hours, Half day, Full day'
            }),
            'is_available': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        help_texts = {
            'price': 'Price in local currency',
            'duration': 'How long the activity takes',
            'is_available': 'Check if this activity is currently available',
        }
    
    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name:
            name = ' '.join(name.split())
            if len(name) < 3:
                raise forms.ValidationError("Activity name must be at least 3 characters long.")
        return name
    
    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price and price < 0:
            raise forms.ValidationError("Price cannot be negative.")
        return price


class PlaceReviewForm(forms.ModelForm):
    """Form for user reviews"""
    
    rating = forms.IntegerField(
        min_value=1,
        max_value=5,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': 1,
            'max': 5,
            'step': 1
        })
    )
    
    review = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Share your experience about this place...'
        }),
        required=True
    )
    
    class Meta:
        model = PlaceReview
        fields = [
            "rating",
            "review"
        ]
    
    def clean_rating(self):
        rating = self.cleaned_data.get('rating')
        if rating:
            if rating < 1 or rating > 5:
                raise forms.ValidationError("Rating must be between 1 and 5.")
        return rating
    
    def clean_review(self):
        review = self.cleaned_data.get('review')
        if review:
            review = review.strip()
            if len(review) < 10:
                raise forms.ValidationError("Please write at least 10 characters for your review.")
            if len(review) > 2000:
                raise forms.ValidationError("Review cannot exceed 2000 characters.")
        return review


# Formset for handling multiple images
from django.forms import inlineformset_factory

DestinationImageFormSet = inlineformset_factory(
    Destination,
    DestinationImage,
    form=DestinationImageForm,
    fields=['image'],
    extra=5,
    max_num=20,
    can_delete=True,
    can_delete_extra=True
)

PlaceImageFormSet = inlineformset_factory(
    DestinationPlace,
    PlaceImage,
    form=PlaceImageForm,
    fields=['image'],
    extra=5,
    max_num=20,
    can_delete=True,
    can_delete_extra=True
)

PlaceActivityFormSet = inlineformset_factory(
    DestinationPlace,
    PlaceActivity,
    form=PlaceActivityForm,
    fields=['name', 'description', 'price', 'duration', 'is_available'],
    extra=3,
    max_num=10,
    can_delete=True,
    can_delete_extra=True
)