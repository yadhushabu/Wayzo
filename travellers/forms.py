from django import forms

from agencies.models import CancellationPolicy, TourPackage
from .models import PropertyBooking, TravellerProfile, ProfilePost

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