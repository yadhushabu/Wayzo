

# Create your views here.

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from restaurants.models import RestaurantProfile
from agencies.models import AgencyProfile

@login_required
def traveller_dashboard(request):

    restaurants = RestaurantProfile.objects.filter(is_approved=True)
    agencies = AgencyProfile.objects.filter(is_approved=True)

    return render(request, "travellers/dashboard.html", {
        "restaurants": restaurants,
        "agencies": agencies
    })


