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


# ✅ POST FORM
class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ["title", "content"]


# ✅ POST IMAGES
PostImageFormSet = modelformset_factory(
    PostImage,
    fields=("image",),
    extra=2,  # allow multiple uploads
    can_delete=True
)


# ✅ TRIP FORM
class TripForm(forms.ModelForm):
    class Meta:
        model = Trip
        exclude = ["creator", "community"]


# ✅ TRIP IMAGES
TripImageFormSet = modelformset_factory(
    TripImage,
    fields=("image",),
    extra=2
)


# ✅ TRIP ITINERARY
TripItineraryFormSet = modelformset_factory(
    TripItinerary,
    fields=("day_number", "title", "description"),
    extra=3  # user can add days
)