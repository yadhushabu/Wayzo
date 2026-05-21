from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required

from django.db.models import Avg

from .models import (
    Destination,
    DestinationImage,
    DestinationPlace,
    PlaceImage,
    PlaceActivity,
    PlaceReview
)

from .forms import (
    DestinationForm,
    DestinationPlaceForm,
    PlaceReviewForm
)


import json
import requests
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.files.images import get_image_dimensions
from .models import DestinationPlace, DestinationImage
from .forms import DestinationForm

from django.http import HttpResponseForbidden


def can_edit(user, obj):

    if user.is_staff or user.is_superuser:
        return True

    return obj.created_by == user

@login_required
def add_destination(request):
    google_api_key = getattr(settings, 'GOOGLE_API_KEY', '')
    openweather_api_key = getattr(settings, 'OPENWEATHER_API_KEY', '')
    
    if request.method == "POST":
        print("="*50)
        print("POST request received")
        print("POST data:", request.POST)
        print("FILES:", request.FILES)
        print("="*50)
        
        form = DestinationForm(request.POST)
        
        if form.is_valid():
            print("✅ Form is valid!")
            destination = form.save(commit=False)
            destination.created_by = request.user
            destination.is_approved = request.user.is_staff or request.user.is_superuser
            
            # Handle coordinates
            latitude = request.POST.get('latitude')
            longitude = request.POST.get('longitude')
            if latitude and longitude:
                destination.latitude = float(latitude)
                destination.longitude = float(longitude)
            
            # Handle best_months
            best_months = request.POST.get('best_months', '')
            if best_months:
                destination.best_months = best_months
            
            destination.save()
            print(f"✅ Destination saved: {destination.name}")
            
            # Handle images
            images = request.FILES.getlist("images")
            print(f"📸 Processing {len(images)} images")
            
            for img in images:
                DestinationImage.objects.create(
                    destination=destination,
                    image=img
                )
                print(f"  ✅ Saved image: {img.name}")
            
            messages.success(request, f"✨ Destination '{destination.name}' added successfully!")
            
            # FIXED: Redirect to destination_list (which is the root path '/destinations/')
            return redirect('destinations:destination_list')
            
        else:
            print("❌ Form is invalid!")
            print("Form errors:", form.errors)
            messages.error(request, "Please correct the errors below.")
    else:
        form = DestinationForm()
    
    return render(request, "destinations/add_destination.html", {
        "form": form,
        "google_api_key": google_api_key,
        "openweather_api_key": openweather_api_key,
    })

def fetch_coordinates(destination_name, google_api_key=None, openweather_api_key=None):
    """Fetch coordinates using multiple APIs with fallback"""
    
    if not destination_name:
        return None
    
    # Try Google Geocoding API first
    if google_api_key:
        try:
            url = f"https://maps.googleapis.com/maps/api/geocode/json?address={requests.utils.quote(destination_name)}&key={google_api_key}"
            response = requests.get(url, timeout=10)
            data = response.json()
            
            if data.get('status') == 'OK' and data.get('results'):
                location = data['results'][0]['geometry']['location']
                return {'lat': location['lat'], 'lng': location['lng']}
        except Exception as e:
            print(f"Google Geocoding error: {e}")
    
    # Fallback to OpenWeather Geocoding API
    if openweather_api_key:
        try:
            url = f"http://api.openweathermap.org/geo/1.0/direct?q={requests.utils.quote(destination_name)}&limit=1&appid={openweather_api_key}"
            response = requests.get(url, timeout=10)
            data = response.json()
            
            if data and len(data) > 0:
                return {'lat': data[0]['lat'], 'lng': data[0]['lon']}
        except Exception as e:
            print(f"OpenWeather Geocoding error: {e}")
    
    return None

def fetch_destination_info(destination_name, serpapi_key):
    """Fetch additional destination information using SerpAPI (Google Search)"""
    
    if not serpapi_key or not destination_name:
        return None
    
    try:
        url = "https://serpapi.com/search"
        params = {
            "q": f"{destination_name} destination description travel",
            "api_key": serpapi_key,
            "engine": "google",
            "num": 5
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        # Extract knowledge graph info if available
        info = {}
        if 'knowledge_graph' in data:
            kg = data['knowledge_graph']
            if 'description' in kg:
                info['description'] = kg['description']
            if 'latitude' in kg and 'longitude' in kg:
                info['latitude'] = kg['latitude']
                info['longitude'] = kg['longitude']
        
        return info if info else None
        
    except Exception as e:
        print(f"SerpAPI error: {e}")
        return None

# Optional: AJAX endpoint for fetching coordinates dynamically
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

@require_http_methods(["GET"])
def get_coordinates_api(request):
    """AJAX endpoint to fetch coordinates"""
    destination_name = request.GET.get('name', '').strip()
    
    if not destination_name:
        return JsonResponse({'error': 'Destination name required'}, status=400)
    
    google_api_key = getattr(settings, 'GOOGLE_API_KEY', '')
    openweather_api_key = getattr(settings, 'OPENWEATHER_API_KEY', '')
    
    coordinates = fetch_coordinates(destination_name, google_api_key, openweather_api_key)
    
    if coordinates:
        return JsonResponse({
            'success': True,
            'latitude': coordinates['lat'],
            'longitude': coordinates['lng']
        })
    else:
        return JsonResponse({
            'success': False,
            'error': 'Could not fetch coordinates'
        }, status=404)


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from .models import Destination, DestinationPlace, PlaceImage, PlaceActivity
from .forms import DestinationPlaceForm

@login_required
def add_place(request, destination_id):
    destination = get_object_or_404(Destination, id=destination_id)
    google_api_key = getattr(settings, 'GOOGLE_API_KEY', '')
    
    if request.method == "POST":
        print("="*50)
        print("POST request received for adding place")
        print("POST data:", request.POST)
        print("FILES:", request.FILES)
        print("="*50)
        
        form = DestinationPlaceForm(request.POST)
        
        if form.is_valid():
            try:
                place = form.save(commit=False)
                place.destination = destination
                place.created_by = request.user
                place.is_approved = request.user.is_staff or request.user.is_superuser
                
                # Handle coordinates
                latitude = request.POST.get('latitude')
                longitude = request.POST.get('longitude')
                if latitude and longitude:
                    place.latitude = float(latitude)
                    place.longitude = float(longitude)
                
                # Handle best months
                best_months = request.POST.get('best_months_to_visit', '')
                if best_months:
                    place.best_months_to_visit = best_months
                
                # Handle preferred weather
                preferred_weather = request.POST.get('preferred_weather', '')
                if preferred_weather:
                    place.preferred_weather = preferred_weather
                
                # Handle features
                place.best_for_photography = request.POST.get('best_for_photography') == 'true'
                place.best_for_sunset = request.POST.get('best_for_sunset') == 'true'
                place.best_for_sunrise = request.POST.get('best_for_sunrise') == 'true'
                place.is_hidden_gem = request.POST.get('is_hidden_gem') == 'true'
                
                # Handle priority score (admin only)
                if request.user.is_staff:
                    priority_score = request.POST.get('priority_score')
                    if priority_score:
                        place.priority_score = int(priority_score)
                
                place.save()
                print(f"✅ Place saved: {place.name}")
                
                # Handle images
                images = request.FILES.getlist("images")
                print(f"📸 Processing {len(images)} images")
                
                for img in images:
                    PlaceImage.objects.create(
                        place=place,
                        image=img
                    )
                    print(f"  ✅ Saved image: {img.name}")
                
                # Handle activities
                activity_names = request.POST.getlist("activity_name")
                activity_prices = request.POST.getlist("activity_price")
                activity_durations = request.POST.getlist("activity_duration")
                activity_descriptions = request.POST.getlist("activity_description")
                
                for i in range(len(activity_names)):
                    if activity_names[i] and activity_names[i].strip():
                        price = float(activity_prices[i]) if activity_prices[i] else 0
                        PlaceActivity.objects.create(
                            place=place,
                            name=activity_names[i],
                            price=price,
                            duration=activity_durations[i] if i < len(activity_durations) else "",
                            description=activity_descriptions[i] if i < len(activity_descriptions) else "",
                            is_available=True
                        )
                        print(f"  ✅ Saved activity: {activity_names[i]}")
                
                messages.success(request, f'✨ "{place.name}" has been added successfully!')
                return redirect('destinations:place_detail', place_id=place.id)
                
            except Exception as e:
                print(f"❌ Error saving place: {e}")
                messages.error(request, f"Error saving place: {str(e)}")
        else:
            print("❌ Form is invalid!")
            print("Form errors:", form.errors)
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = DestinationPlaceForm()
    
    return render(request, "destinations/add_place.html", {
        "form": form,
        "destination": destination,
        "google_api_key": google_api_key,
    })



def destination_detail(request, destination_id):
    destination = get_object_or_404(Destination, id=destination_id)
    
    # Get places
    famous_places = destination.places.filter(is_approved=True, is_hidden_gem=False)
    hidden_gems = destination.places.filter(is_approved=True, is_hidden_gem=True)
    all_places = destination.places.filter(is_approved=True)
    
    # Get reviews
    from .models import PlaceReview
    reviews = PlaceReview.objects.filter(place__destination=destination).order_by('-created_at')
    
    # Get weather data
    from .services.weather_service import WeatherService
    weather_data = WeatherService.get_weather(destination.city or destination.name)
    
    context = {
        'destination': destination,
        'famous_places': famous_places,
        'hidden_gems': hidden_gems,
        'all_places': all_places,
        'reviews': reviews,
        'weather_data': weather_data,
    }
    
    return render(request, "destinations/destination_detail.html", context)

# views.py
from django.db.models import Avg
from django.contrib import messages

@login_required
def add_review(request, place_id):
    place = get_object_or_404(DestinationPlace, id=place_id)
    
    # Check if user already reviewed this place
    existing_review = PlaceReview.objects.filter(place=place, user=request.user).first()
    if existing_review:
        messages.warning(request, "You have already reviewed this place. You can edit your existing review.")
        return redirect('destinations:place_detail', place_id=place.id)
    
    if request.method == "POST":
        rating = request.POST.get('rating')
        review_text = request.POST.get('review')
        
        # Validate
        if not rating or not review_text:
            messages.error(request, "Please provide both rating and review")
            return redirect('destinations:add_review', place_id=place.id)
        
        try:
            # Create review
            review = PlaceReview.objects.create(
                place=place,
                user=request.user,
                rating=int(rating),
                review=review_text.strip()
            )
            
            # Update place stats
            place.total_reviews = place.reviews.count()
            place.average_rating = place.reviews.aggregate(Avg('rating'))['rating__avg'] or 0
            place.save()
            
            messages.success(request, f"✅ Thank you for your review! You rated {place.name} {rating}/5 stars.")
            return redirect('destinations:place_detail', place_id=place.id)
            
        except Exception as e:
            messages.error(request, f"Error saving review: {str(e)}")
            return redirect('destinations:add_review', place_id=place.id)
    
    return render(request, "destinations/add_review.html", {"place": place})


def destination_list(request):

    destinations = Destination.objects.filter(
        is_approved=True
    ).prefetch_related("images")

    return render(request, "destinations/destination_list.html", {
        "destinations": destinations
    })


def place_detail(request, place_id):
    place = get_object_or_404(DestinationPlace, id=place_id, is_approved=True)
    
    # Get weather data
    from .services.weather_service import WeatherService
    weather_data = WeatherService.get_weather(place.destination.city or place.destination.name)
    
    # Get ranking engine score
    from .services.ranking_engine import RankingEngine
    engine = RankingEngine()
    popularity_score = engine.calculate(
        city=place.destination.city or place.destination.name,
        attractions_count=1,
        rating=place.average_rating
    )
    
    context = {
        'place': place,
        'gallery': place.images.all(),
        'activities': place.activities.filter(is_available=True),
        'reviews': place.reviews.select_related('user').order_by('-created_at'),
        'weather_data': weather_data,
        'popularity_score': popularity_score,
    }
    
    return render(request, "destinations/place_detail.html", context)

@login_required
def edit_destination(request, destination_id):

    destination = get_object_or_404(
        Destination,
        id=destination_id
    )

    # PERMISSION CHECK
    if not can_edit(request.user, destination):
        return HttpResponseForbidden("You cannot edit this destination.")

    if request.method == "POST":

        form = DestinationForm(
            request.POST,
            instance=destination
        )

        if form.is_valid():

            destination = form.save()

            # OPTIONAL NEW IMAGES
            images = request.FILES.getlist("images")

            for img in images:
                DestinationImage.objects.create(
                    destination=destination,
                    image=img
                )

            return redirect(
                "destinations:destination_detail",
                destination.id
            )

    else:

        form = DestinationForm(instance=destination)

    return render(
        request,
        "destinations/edit_destination.html",
        {
            "form": form,
            "destination": destination
        }
    )


@login_required
def edit_place(request, place_id):
    place = get_object_or_404(DestinationPlace, id=place_id)
    
    # Check permissions
    if request.user != place.created_by and not request.user.is_staff:
        messages.error(request, "You don't have permission to edit this place.")
        return redirect('destinations:place_detail', place_id=place.id)
    
    if request.method == "POST":
        form = DestinationPlaceForm(request.POST, instance=place)
        
        if form.is_valid():
            place = form.save(commit=False)
            
            # Handle coordinates
            latitude = request.POST.get('latitude')
            longitude = request.POST.get('longitude')
            if latitude and longitude:
                place.latitude = float(latitude)
                place.longitude = float(longitude)
            
            place.save()
            
            # Handle image deletion
            delete_images = request.POST.getlist('delete_images')
            if delete_images:
                PlaceImage.objects.filter(id__in=delete_images, place=place).delete()
            
            # Handle new images
            images = request.FILES.getlist("images")
            for img in images:
                PlaceImage.objects.create(place=place, image=img)
            
            messages.success(request, f'✅ "{place.name}" has been updated successfully!')
            return redirect('destinations:place_detail', place_id=place.id)
    else:
        form = DestinationPlaceForm(instance=place)
    
    context = {
        'form': form,
        'place': place,
        'existing_images': place.images.all(),
        'google_api_key': settings.GOOGLE_API_KEY,
    }
    
    return render(request, "destinations/edit_place.html", context)


from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from .models import Destination


@login_required
def delete_destination(request, destination_id):

    destination = get_object_or_404(Destination, id=destination_id)

    # only owner or admin can delete
    if request.user != destination.created_by and not request.user.is_staff:
        return redirect("destinations:destination_detail", destination.id)

    destination.delete()

    return redirect("destinations:destination_list")

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Avg
from .models import DestinationPlace, PlaceReview

@login_required
def edit_review(request, review_id):
    review = get_object_or_404(PlaceReview, id=review_id)
    
    # Check permission - only the review author can edit
    if review.user != request.user:
        messages.error(request, "You don't have permission to edit this review.")
        return redirect('destinations:place_detail', place_id=review.place.id)
    
    if request.method == "POST":
        rating = request.POST.get('rating')
        review_text = request.POST.get('review')
        
        if not rating or not review_text:
            messages.error(request, "Please provide both rating and review")
            return redirect('destinations:edit_review', review_id=review.id)
        
        # Update review
        review.rating = int(rating)
        review.review = review_text.strip()
        review.save()
        
        # Update place stats
        place = review.place
        place.total_reviews = place.reviews.count()
        place.average_rating = place.reviews.aggregate(Avg('rating'))['rating__avg'] or 0
        place.save()
        
        messages.success(request, "✅ Your review has been updated successfully!")
        return redirect('destinations:place_detail', place_id=review.place.id)
    
    return render(request, "destinations/edit_review.html", {"review": review})

@login_required
def delete_review(request, review_id):
    review = get_object_or_404(PlaceReview, id=review_id)
    
    # Check permission
    if review.user != request.user:
        messages.error(request, "You don't have permission to delete this review.")
        return redirect('destinations:place_detail', place_id=review.place.id)
    
    place_id = review.place.id
    review.delete()
    
    # Update place stats
    place = review.place
    place.total_reviews = place.reviews.count()
    place.average_rating = place.reviews.aggregate(Avg('rating'))['rating__avg'] or 0
    place.save()
    
    messages.success(request, "✅ Your review has been deleted.")
    return redirect('destinations:place_detail', place_id=place_id)