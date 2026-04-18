from django import forms
from .models import AgencyProfile, CancellationPolicy, TourPackage, PackageItinerary, PackageImage
from django.forms import inlineformset_factory


class AgencyProfileEditForm(forms.ModelForm):

    class Meta:
        model = AgencyProfile
        fields = [
            "description",
            "experience_years",
            "tour_packages",
            "flight_booking",
            "cab_service",
            "visa_service",
            "travel_insurance",
            "website",
            "instagram",
        ]


class TourPackageForm(forms.ModelForm):

    is_featured = forms.BooleanField(required=False)
    is_active = forms.BooleanField(required=False, initial=True)
    
    # Add custom widgets for better UX
    min_booking_days = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=365,
        initial=1,
        widget=forms.NumberInput(attrs={'placeholder': 'e.g., 7'})
    )
    max_booking_days = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=730,
        initial=365,
        widget=forms.NumberInput(attrs={'placeholder': 'e.g., 90'})
    )
    
    best_season = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'e.g., October to March, Summer, Winter'})
    )
    
    difficulty_level = forms.ChoiceField(
        choices=TourPackage.DIFFICULTY_LEVELS,
        required=False,
        initial='moderate',
        widget=forms.Select()
    )

    class Meta:
        model = TourPackage
        fields = [
            "title",
            "description",
            "duration_days",
            "duration_nights",
            "places_covered",
            "min_group_size",
            "max_group_size",
            "guide_language",
            "price",
            "discounted_price",
            "best_season",  # NEW
            "difficulty_level",  # NEW
            "min_booking_days",  # NEW
            "max_booking_days",  # NEW
            "pickup_points",
            "drop_points",
            "accommodation_type",
            "transport_type",
            "meals",
            "suitable_for",
            "things_to_carry",
            "inclusions",
            "exclusions",
            "cancellation_policy",
            "terms_conditions",
            "is_featured",
            "is_active",
        ]
        
    def clean(self):
        cleaned_data = super().clean()
        price = cleaned_data.get('price')
        discounted_price = cleaned_data.get('discounted_price')
        
        if discounted_price and discounted_price >= price:
            raise forms.ValidationError(
                "Discounted price should be less than the original price."
            )
        
        min_group_size = cleaned_data.get('min_group_size')
        max_group_size = cleaned_data.get('max_group_size')
        
        if min_group_size and max_group_size and min_group_size > max_group_size:
            raise forms.ValidationError(
                "Minimum group size cannot be greater than maximum group size."
            )
        
        # Validate booking days
        min_booking_days = cleaned_data.get('min_booking_days')
        max_booking_days = cleaned_data.get('max_booking_days')
        
        if min_booking_days and max_booking_days and min_booking_days > max_booking_days:
            raise forms.ValidationError(
                "Minimum booking days cannot be greater than maximum booking days."
            )
        
        return cleaned_data


class PackageItineraryForm(forms.ModelForm):
    
    class Meta:
        model = PackageItinerary
        fields = [
            "day_number",
            "title",
            "description",
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Describe the activities, meals, and highlights for this day...'}),
            'title': forms.TextInput(attrs={'placeholder': 'e.g., Arrival and City Tour'}),
            'day_number': forms.NumberInput(attrs={'min': 1}),
        }


class PackageImageForm(forms.ModelForm):
    
    class Meta:
        model = PackageImage
        fields = ["image"]
        widgets = {
            'image': forms.FileInput(attrs={'accept': 'image/*'}),
        }


class CancellationPolicyForm(forms.ModelForm):
    class Meta:
        model = CancellationPolicy
        fields = ["days_before", "refund_percentage"]
        widgets = {
            'days_before': forms.NumberInput(attrs={'min': 0, 'step': 1, 'placeholder': 'e.g., 30'}),
            'refund_percentage': forms.NumberInput(attrs={'min': 0, 'max': 100, 'step': 1, 'placeholder': 'e.g., 100'}),
        }


# Formset definitions
PackageItineraryFormSet = inlineformset_factory(
    TourPackage,
    PackageItinerary,
    form=PackageItineraryForm,
    extra=0,
    can_delete=True,
    min_num=0,
    validate_min=False,
    max_num=30,
    validate_max=False,
)

PackageImageFormSet = inlineformset_factory(
    TourPackage,
    PackageImage,
    form=PackageImageForm,
    extra=1,
    can_delete=True,
    min_num=0,
    validate_min=False,
    max_num=20,
    validate_max=False,
)

# Add this - the correct CancellationPolicy FormSet
CancellationPolicyFormSet = inlineformset_factory(
    TourPackage,
    CancellationPolicy,
    form=CancellationPolicyForm,
    extra=1,  # Start with 1 empty form
    can_delete=True,
    min_num=0,
    validate_min=False,
    max_num=10,
    validate_max=False,
)