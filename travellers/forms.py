from django import forms

from agencies.models import CancellationPolicy, TourPackage
from .models import TravellerProfile, ProfilePost

class TravellerProfileEditForm(forms.ModelForm):

    profile_picture = forms.ImageField(required=False)

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
            "cover_image",
        ]

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):

        profile = super().save(commit=False)

        picture = self.cleaned_data.get("profile_picture")

        if picture:
            self.user.profile_picture = picture

            if commit:
                self.user.save()

        if commit:
            profile.save()

        return profile


class NewPostForm(forms.ModelForm):
    class Meta:
        model = ProfilePost
        fields = ['caption', 'image', 'location']
