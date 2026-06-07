# community/forms.py

from django import forms
from .models import Community, Post, PostImage, Trip, TripImage, TripItinerary
from django.forms import modelformset_factory


# ✅ COMMUNITY FORM
class CommunityForm(forms.ModelForm):
    class Meta:
        model = Community
        fields = [
            "name",
            "description",
            "interest",
            "community_type",
            "cover_image",
            "rules",
            "allow_post",
            "allow_trip",
            "max_members",
            "tags",
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Community name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Describe your community'}),
            'interest': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Adventure, Culture, Food'}),
            'community_type': forms.Select(attrs={'class': 'form-control'}),
            'cover_image': forms.FileInput(attrs={'class': 'form-control'}),
            'rules': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Community rules and guidelines'}),
            'allow_post': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'allow_trip': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'max_members': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Max members (optional)'}),
            'tags': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Comma separated tags'}),
        }


# ✅ POST FORM
class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['title', 'content']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Give your post an engaging title...'
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 6,
                'placeholder': 'Share your travel experience, tips, or story in detail...'
            }),
        }


# ✅ POST IMAGE FORM
class PostImageForm(forms.ModelForm):
    class Meta:
        model = PostImage
        fields = ['image']
        widgets = {
            'image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
        }


# ✅ POST IMAGES FORMSET - Using modelformset_factory
PostImageFormSet = modelformset_factory(
    PostImage,
    form=PostImageForm,
    extra=5,  # Allow up to 5 images
    max_num=5,  # Maximum 5 images
    can_delete=True
)


class TripForm(forms.ModelForm):

    class Meta:
        model = Trip
        

        # ❗ include ONLY user-editable fields
        fields = [
            "title",
            "description",
            "duration_days",
            "duration_nights",
            "places_covered",
            "budget",
            "trip_type",
            "start_date",
            "end_date",
            "rules",
            "max_members",
            "cancellation_policy",
            "inclusions",
            "exclusions",
            "things_to_pack",
            "join_type",
            "visibility",
            "live_tracking_enabled",
            "is_active",
        ]

        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "Trip title"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "duration_days": forms.NumberInput(attrs={"class": "form-control"}),
            "duration_nights": forms.NumberInput(attrs={"class": "form-control"}),
            "places_covered": forms.TextInput(attrs={"class": "form-control"}),
            "budget": forms.NumberInput(attrs={"class": "form-control"}),
            "trip_type": forms.TextInput(attrs={"class": "form-control"}),

            "start_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "end_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),

            "rules": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "max_members": forms.NumberInput(attrs={"class": "form-control"}),

            "cancellation_policy": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "inclusions": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "exclusions": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "things_to_pack": forms.Textarea(attrs={"class": "form-control", "rows": 3}),

            "join_type": forms.Select(attrs={"class": "form-control"}),
            "visibility": forms.Select(attrs={"class": "form-control"}),

            "live_tracking_enabled": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

# ✅ TRIP IMAGES FORMSET
TripImageFormSet = modelformset_factory(
    TripImage,
    fields=("image",),
    extra=5,
    max_num=5,
    can_delete=True
)

TripItineraryFormSet = modelformset_factory(
    TripItinerary,
    fields=("day_number", "title", "description"),
    extra=5,
    max_num=15,
    can_delete=True
)