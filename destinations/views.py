from django.db import models
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from admin_app.utils import create_audit_log

from django.db.models import Avg

from .models import (
    Destination,
    DestinationImage,
    DestinationPlace,
    DestinationReview,
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

from django.http import Http404, HttpResponseForbidden


def can_edit(user, obj):

    if user.is_staff or user.is_superuser:
        return True

    return obj.created_by == user

@login_required
def add_destination(request):

    google_api_key = getattr(settings, 'GOOGLE_API_KEY', '')
    openweather_api_key = getattr(settings, 'OPENWEATHER_API_KEY', '')

    if request.method == "POST":

        form = DestinationForm(request.POST)

        if form.is_valid():

            print("✅ Form is valid!")

            destination = form.save(commit=False)

            destination.created_by = request.user

            # auto approve admin uploads
            destination.is_approved = (
                request.user.is_staff or request.user.is_superuser
            )


            destination.save()

            print(f"✅ Destination saved: {destination.name}")

            create_audit_log(
                user=request.user,
                action='destination_added',
                description=f'Added destination: {destination.name}'
            )

            # images
            images = request.FILES.getlist("images")

            print(f"📸 Processing {len(images)} images")

            for img in images:

                DestinationImage.objects.create(
                    destination=destination,
                    image=img
                )

                print(f"✅ Saved image: {img.name}")

            messages.success(
                request,
                f"✨ Destination '{destination.name}' added successfully!"
            )

            return redirect('destinations:destination_list')

        else:

            print("❌ Form is invalid!")
            print("Form errors:", form.errors)

            messages.error(
                request,
                "Please correct the errors below."
            )

    else:
        form = DestinationForm()

    # ✅ DYNAMIC BASE TEMPLATE
    base_template = (
        "admin_app/base.html"
        if request.user.is_staff or request.user.is_superuser
        else "travellers/base.html"
    )
    
    score_breakdown = [
    ("Manual Priority", 20, "teal"),
    ("Weather Score", 20, "teal"),
    ("Seasonal Score", 20, "teal"),
    ("Popularity", 30, "teal"),
    ("Usage", 10, "teal"),
]
    return render(request, "destinations/add_destination.html", {
        "form": form,
        "google_api_key": google_api_key,
        "openweather_api_key": openweather_api_key,
        "base_template": base_template,   # ✅ IMPORTANT
        "score_breakdown": score_breakdown,
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

    destination = get_object_or_404(
        Destination,
        id=destination_id
    )

    google_api_key = getattr(
        settings,
        'GOOGLE_API_KEY',
        ''
    )

    if request.method == "POST":

        print("=" * 50)
        print("POST request received for adding place")
        print("POST data:", request.POST)
        print("FILES:", request.FILES)
        print("=" * 50)

        form = DestinationPlaceForm(
            request.POST,
            user=request.user
        )

        if form.is_valid():

            try:

                place = form.save(commit=False)

                place.destination = destination
                place.created_by = request.user

                # auto approve for admin
                place.is_approved = (
                    request.user.is_staff
                    or request.user.is_superuser
                )


                # admin-only manual score
                if request.user.is_staff:

                    manual_priority_score = request.POST.get(
                        'manual_priority_score'
                    )

                    if manual_priority_score:

                        place.manual_priority_score = float(
                            manual_priority_score
                        )

                existing = DestinationPlace.objects.filter(
                    destination=destination,
                    name=request.POST.get("name"),
                    created_by=request.user
                ).exists()

                if existing:
                    messages.warning(request, "This place already exists.")
                    return redirect("destinations:destination_detail", destination.id)

                place.save()

                print(f"✅ Place saved: {place.name}")

                create_audit_log(
                    user=request.user,
                    action='place_added',
                    description=f'Added place: {place.name}'
                )

                # images
                images = request.FILES.getlist("images")

                print(f"📸 Processing {len(images)} images")

                for img in images:

                    PlaceImage.objects.create(
                        place=place,
                        image=img
                    )

                    print(f"✅ Saved image: {img.name}")

                # activities
                activity_names = request.POST.getlist(
                    "activity_name"
                )

                activity_prices = request.POST.getlist(
                    "activity_price"
                )

                activity_durations = request.POST.getlist(
                    "activity_duration"
                )

                activity_descriptions = request.POST.getlist(
                    "activity_description"
                )

                for i in range(len(activity_names)):

                    if (
                        activity_names[i]
                        and activity_names[i].strip()
                    ):

                        price = (
                            float(activity_prices[i])
                            if activity_prices[i]
                            else 0
                        )

                        PlaceActivity.objects.create(
                            place=place,
                            name=activity_names[i],
                            price=price,
                            duration=(
                                activity_durations[i]
                                if i < len(activity_durations)
                                else ""
                            ),
                            description=(
                                activity_descriptions[i]
                                if i < len(activity_descriptions)
                                else ""
                            ),
                            is_available=True
                        )

                        print(
                            f"✅ Saved activity: {activity_names[i]}"
                        )

                messages.success(
                    request,
                    f'✨ "{place.name}" has been added successfully!'
                )

                return redirect(
    'destinations:place_detail',
    destination_id=destination.id,
    place_id=place.id
)
            except Exception as e:

                print(f"❌ Error saving place: {e}")

                messages.error(
                    request,
                    f"Error saving place: {str(e)}"
                )

        else:

            print("❌ Form is invalid!")
            print("Form errors:", form.errors)

            for field, errors in form.errors.items():

                for error in errors:

                    messages.error(
                        request,
                        f"{field}: {error}"
                    )

    else:

        form = DestinationPlaceForm(
            user=request.user
        )

    # dynamic base template
    base_template = (
        "admin_app/base.html"
        if request.user.is_staff or request.user.is_superuser
        else "travellers/base.html"
    )

    return render(
        request,
        "destinations/add_place.html",
        {
            "form": form,
            "destination": destination,
            "google_api_key": google_api_key,
            "base_template": base_template,
        }
    )



from django.http import Http404

def destination_detail(request, destination_id):

    destination = get_object_or_404(
        Destination,
        id=destination_id
    )

    # =====================================================
    # APPROVAL CHECK
    # =====================================================

    if (
        not destination.is_approved
        and request.user != destination.created_by
        and not request.user.is_staff
        and not request.user.is_superuser
    ):
        raise Http404("Destination not approved yet.")

    # =====================================================
    # PLACES
    # =====================================================

    if (
        request.user.is_staff
        or request.user.is_superuser
        or request.user == destination.created_by
    ):

        famous_places = destination.places.filter(
            is_hidden_gem=False
        )

        hidden_gems = destination.places.filter(
            is_hidden_gem=True
        )

        all_places = destination.places.all().order_by(
            "-final_trending_score",
            "-average_rating"
        )

    else:

        famous_places = destination.places.filter(
            is_approved=True,
            is_hidden_gem=False
        )

        hidden_gems = destination.places.filter(
            is_approved=True,
            is_hidden_gem=True
        )

        all_places = destination.places.filter(
            is_approved=True
        ).order_by(
            "-final_trending_score",
            "-average_rating"
        )

    # =====================================================
    # REVIEWS
    # =====================================================

    reviews = destination.reviews.select_related(
        "user"
    ).order_by("-created_at")

    # =====================================================
    # WEATHER
    # =====================================================

    from .services.weather_service import WeatherService

    weather_data = WeatherService.get_weather(
        destination.city or destination.name
    )

    # =====================================================
    # BASE TEMPLATE
    # =====================================================

    base_template = (
        "admin_app/base.html"
        if request.user.is_staff or request.user.is_superuser
        else "travellers/base.html"
    )

    # =====================================================
    # CONTEXT
    # =====================================================

    context = {
        "destination": destination,
        "famous_places": famous_places,
        "hidden_gems": hidden_gems,
        "all_places": all_places,
        "reviews": reviews,
        "weather_data": weather_data,
        "base_template": base_template,
    }

    return render(
        request,
        "destinations/destination_detail.html",
        context
    )


from django.db.models import Avg
from django.contrib import messages

@login_required
def add_review(request, place_id):

    place = get_object_or_404(DestinationPlace, id=place_id)

    existing_review = PlaceReview.objects.filter(
        place=place,
        user=request.user
    ).first()

    if existing_review:
        messages.warning(request, "You already reviewed this place.")
        return redirect(
            'destinations:place_detail',
            destination_id=place.destination.id,
            place_id=place.id
        )

    if request.method == "POST":

        rating = request.POST.get('rating')
        review_text = request.POST.get('review')

        if not rating or not review_text:
            messages.error(request, "Please provide both rating and review.")
            return redirect(
                'destinations:add_review',
                place_id=place.id
            )

        try:
            review = PlaceReview.objects.create(
                place=place,
                user=request.user,
                rating=int(rating),
                review=review_text.strip()
            )
            
            create_audit_log(
                user=request.user,
                action='place_review_added',
                description=f'Reviewed place: {place.name}'
            )
            
            # IMPORTANT: you still need your stats method implemented
            place.refresh_review_stats()

            messages.success(request, f"✅ Review added for {place.name}")

            return redirect(
                'destinations:place_detail',
                destination_id=place.destination.id,
                place_id=place.id
            )

        except Exception as e:
            messages.error(request, f"Error saving review: {str(e)}")
            return redirect(
                'destinations:add_review',
                place_id=place.id
            )

    base_template = (
        "admin_app/base.html"
        if request.user.is_staff or request.user.is_superuser
        else "travellers/base.html"
    )

    return render(request, "destinations/add_review.html", {
        "place": place,
        "base_template": base_template
    })


from django.db.models import Q
 
def destination_list(request):
 
    # ── Base queryset ──────────────────────────────────────────
    if request.user.is_staff or request.user.is_superuser:

        destinations = (
            Destination.objects
            .all()
            .prefetch_related("images", "places")
        )

    elif request.user.is_authenticated:

        destinations = (
            Destination.objects
            .filter(
                Q(is_approved=True) |
                Q(created_by=request.user)
            )
            .distinct()
            .prefetch_related("images", "places")
        )

    else:

        destinations = (
            Destination.objects
            .filter(is_approved=True)
            .prefetch_related("images", "places")
        )
 
    # ── Search ─────────────────────────────────────────────────
    search = request.GET.get("search", "").strip()
    if search:
        destinations = destinations.filter(
            Q(name__icontains=search) |
            Q(city__icontains=search) |
            Q(country__icontains=search) |
            Q(state__icontains=search) |
            Q(description__icontains=search)
        )
 
    # ── Category (maps to destination name/description keywords) ──
    category = request.GET.get("category", "").strip()
    if category and category != "all":
        destinations = destinations.filter(
            Q(name__icontains=category) |
            Q(description__icontains=category) |
            Q(city__icontains=category)
        )
 
    # ── Best Season ────────────────────────────────────────────
    season = request.GET.get("season", "").strip()
    if season:
        destinations = destinations.filter(best_season=season)
 
    # ── Preferred Weather ──────────────────────────────────────
    weather = request.GET.get("weather", "").strip()
    if weather:
        destinations = destinations.filter(preferred_weather=weather)
 
    # ── Suitable For (filters via places) ─────────────────────
    suitable_for = request.GET.get("suitable_for", "").strip()
    if suitable_for:
        destinations = destinations.filter(
            places__suitable_for=suitable_for,
            places__is_approved=True
        ).distinct()
 
    # ── Min Rating ────────────────────────────────────────────
    min_rating = request.GET.get("min_rating", "").strip()
    if min_rating:
        try:
            destinations = destinations.filter(
                average_rating__gte=float(min_rating)
            )
        except ValueError:
            pass
 
    # ── Trending filter ───────────────────────────────────────
    trending = request.GET.get("trending", "").strip()
    if trending == "top10":
        destinations = destinations.order_by("-final_trending_score")[:10]
    elif trending == "top25":
        destinations = destinations.order_by("-final_trending_score")[:25]
    # "rising" handled below in sort
 
    # ── Special filters ───────────────────────────────────────
    special = request.GET.get("special", "").strip()
    if special == "featured":
        destinations = destinations.filter(is_featured=True)
    elif special == "best_now":
        # Filter destinations where is_best_time_now() is True
        # Done in Python since it's a method (not a DB field)
        from datetime import datetime
        current_month = datetime.now().month
        destinations = destinations.filter(
            Q(best_month_start__lte=current_month, best_month_end__gte=current_month) |
            Q(best_month_start__gt=models.F("best_month_end"))  # wraps around year
        )
    elif special == "gems":
        destinations = destinations.filter(
            places__is_hidden_gem=True,
            places__is_approved=True
        ).distinct()
 
    # ── Sorting ───────────────────────────────────────────────
    sort = request.GET.get("sort", "trending").strip()
 
    if sort == "trending" or sort == "ai":
        destinations = destinations.order_by("-final_trending_score", "-average_rating")
    elif sort == "rating":
        destinations = destinations.order_by("-average_rating", "-total_reviews")
    elif sort == "popular":
        destinations = destinations.order_by("-total_views", "-total_reviews")
    elif sort == "newest":
        destinations = destinations.order_by("-created_at")
    elif sort == "weather":
        destinations = destinations.order_by("-weather_score", "-final_trending_score")
    elif sort == "rising":
        # Rising = good score but fewer views (hidden gems of destinations)
        destinations = destinations.order_by("-seasonal_score", "total_views")
    else:
        destinations = destinations.order_by("-final_trending_score", "-average_rating")
 
    # ── Dynamic base template ─────────────────────────────────
    base_template = (
        "admin_app/base.html"
        if request.user.is_staff or request.user.is_superuser
        else "travellers/base.html"
    )
 
    return render(
        request,
        "destinations/destination_list.html",
        {
            "destinations": destinations,
            "base_template": base_template,
        }
    )


def place_detail(request, destination_id, place_id):

    # =====================================================
    # FETCH PLACE (cleaner + safer)
    # =====================================================

    place = get_object_or_404(
        DestinationPlace,
        id=place_id,
        destination_id=destination_id
    )

    # Hide pending places from other users
    if (
        not place.is_approved
        and request.user != place.created_by
        and not request.user.is_staff
        and not request.user.is_superuser
    ):
        raise Http404("Place not approved yet.")

    # =====================================================
    # WEATHER SERVICE
    # =====================================================

    from .services.weather_service import WeatherService

    weather_data = WeatherService.get_weather(
        place.destination.city or place.destination.name
    )

    # =====================================================
    # AI RANKING ENGINE (OPTIONAL DISPLAY ONLY)
    # =====================================================

    from .services.ranking_engine import RankingEngine

    engine = RankingEngine()

    ai_score = engine.calculate(
        city=place.destination.city or place.destination.name,
        attractions_count=place.visit_count or 1,
        rating=place.average_rating
    )

    # =====================================================
    # BASE TEMPLATE
    # =====================================================

    base_template = (
        "admin_app/base.html"
        if request.user.is_staff or request.user.is_superuser
        else "travellers/base.html"
    )

    # =====================================================
    # CONTEXT
    # =====================================================

    context = {

        "place": place,

        "gallery": place.images.all(),

        "activities": place.activities.filter(
            is_available=True
        ).order_by("-price"),

        "reviews": place.reviews.select_related(
            "user"
        ).order_by("-created_at"),

        "weather_data": weather_data,

        # renamed (IMPORTANT FIX)
        "ai_score": round(ai_score, 2),

        # real stored score from DB
        "final_trending_score": place.final_trending_score,

        "base_template": base_template,
    }

    return render(
        request,
        "destinations/place_detail.html",
        context
    )

@login_required
def edit_destination(request, destination_id):

    destination = get_object_or_404(
        Destination,
        id=destination_id
    )

    # ✅ PERMISSION CHECK
    if not can_edit(request.user, destination):

        return HttpResponseForbidden(
            "You cannot edit this destination."
        )

    if request.method == "POST":

        form = DestinationForm(
            request.POST,
            request.FILES,
            instance=destination
        )

        if form.is_valid():

            destination = form.save()

            # ✅ HANDLE COORDINATES
            latitude = request.POST.get("latitude")
            longitude = request.POST.get("longitude")

            if latitude and longitude:

                destination.latitude = float(latitude)
                destination.longitude = float(longitude)

            # ✅ HANDLE BEST MONTHS
            best_months = request.POST.get("best_months")

            if best_months:
                destination.best_months = best_months

            destination.save()

            # ✅ OPTIONAL NEW IMAGES
            images = request.FILES.getlist("images")

            for img in images:

                DestinationImage.objects.create(
                    destination=destination,
                    image=img
                )

            messages.success(
                request,
                f"✅ {destination.name} updated successfully!"
            )

            create_audit_log(
                user=request.user,
                action='destination_updated',
                description=f'Updated destination: {destination.name}'
            )

            return redirect(
                "destinations:destination_detail",
                destination.id
            )

        else:

            messages.error(
                request,
                "Please correct the errors below."
            )

    else:

        form = DestinationForm(instance=destination)

    # ✅ DYNAMIC BASE TEMPLATE
    base_template = (
        "admin_app/base.html"
        if request.user.is_staff or request.user.is_superuser
        else "travellers/base.html"
    )

    return render(
        request,
        "destinations/edit_destination.html",
        {
            "form": form,
            "destination": destination,
            "base_template": base_template
        }
    )


@login_required
def edit_place(request, place_id):

    place = get_object_or_404(
        DestinationPlace,
        id=place_id
    )

    # =====================================================
    # PERMISSION CHECK
    # =====================================================

    if (
        request.user != place.created_by
        and not request.user.is_staff
        and not request.user.is_superuser
    ):

        messages.error(
            request,
            "You don't have permission to edit this place."
        )

        return redirect(
            'destinations:place_detail',
            destination_id=place.destination.id,
            place_id=place.id
        )

    google_api_key = getattr(
        settings,
        'GOOGLE_API_KEY',
        ''
    )

    # =====================================================
    # POST
    # =====================================================

    if request.method == "POST":

        form = DestinationPlaceForm(
            request.POST,
            request.FILES,
            instance=place,
            user=request.user
        )

        if form.is_valid():

            try:

                place = form.save(commit=False)

                # =========================================
                # ADMIN MANUAL SCORE
                # =========================================

                if request.user.is_staff:

                    manual_priority_score = request.POST.get(
                        'manual_priority_score'
                    )

                    if manual_priority_score:

                        place.manual_priority_score = float(
                            manual_priority_score
                        )

                # =========================================
                # SAVE PLACE
                # =========================================

                place.save()

                # =========================================
                # DELETE OLD IMAGES
                # =========================================

                delete_images = request.POST.getlist(
                    'delete_images'
                )

                if delete_images:

                    PlaceImage.objects.filter(
                        id__in=delete_images,
                        place=place
                    ).delete()

                # =========================================
                # ADD NEW IMAGES
                # =========================================

                images = request.FILES.getlist(
                    "images"
                )

                for img in images:

                    PlaceImage.objects.create(
                        place=place,
                        image=img
                    )

                # =========================================
                # SUCCESS
                # =========================================

                messages.success(
                    request,
                    f'✅ "{place.name}" updated successfully!'
                )

                create_audit_log(
                    user=request.user,
                    action='place_updated',
                    description=f'Updated place: {place.name}'
                )

                return redirect(
                    'destinations:place_detail',
                    destination_id=place.destination.id,
                    place_id=place.id
                )

            except Exception as e:

                print("❌ Edit Place Error:", e)

                messages.error(
                    request,
                    f"Error updating place: {str(e)}"
                )

        else:

            print("❌ Form Errors:", form.errors)

            messages.error(
                request,
                "Please correct the errors below."
            )

    # =====================================================
    # GET
    # =====================================================

    else:

        form = DestinationPlaceForm(
            instance=place,
            user=request.user
        )

    # =====================================================
    # DYNAMIC BASE TEMPLATE
    # =====================================================

    base_template = (
        "admin_app/base.html"
        if (
            request.user.is_staff
            or request.user.is_superuser
        )
        else "travellers/base.html"
    )

    # =====================================================
    # CONTEXT
    # =====================================================

    context = {
        'form': form,
        'place': place,
        'existing_images': place.images.all(),
        'google_api_key': google_api_key,
        'base_template': base_template,
    }

    return render(
        request,
        "destinations/edit_place.html",
        context
    )

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from .models import Destination


@login_required
def delete_destination(request, destination_id):

    destination = get_object_or_404(
        Destination,
        id=destination_id
    )

    # ✅ PERMISSION CHECK
    if (
        request.user != destination.created_by
        and not request.user.is_staff
        and not request.user.is_superuser
    ):
        messages.error(
            request,
            "You don't have permission to delete this destination."
        )

        return redirect(
            "destinations:destination_detail",
            destination.id
        )

    if request.method == "POST":
        
        destination_name = destination.name

        create_audit_log(
            user=request.user,
            action='destination_deleted',
            description=f'Deleted destination: {destination_name}'
        )
        destination.delete()

        messages.success(
            request,
            "🗑️ Destination deleted successfully!"
        )

        return redirect("destinations:destination_list")

    # safety fallback (GET request)
    return redirect(
        "destinations:destination_detail",
        destination.id
    )

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Avg
from .models import DestinationPlace, PlaceReview

@login_required
def edit_review(request, review_id):

    review = get_object_or_404(
        PlaceReview,
        id=review_id
    )

    # ✅ PERMISSION CHECK
    if review.user != request.user:

        messages.error(
            request,
            "You don't have permission to edit this review."
        )

        return redirect(
            'destinations:place_detail',
            destination_id=place.destination.id,
            place_id=review.place.id
        )

    if request.method == "POST":

        rating = request.POST.get('rating')
        review_text = request.POST.get('review')

        if not rating or not review_text:

            messages.error(
                request,
                "Please provide both rating and review."
            )

            return redirect(
                'destinations:edit_review',
                review_id=review.id
            )

        # ✅ UPDATE REVIEW
        review.rating = int(rating)
        review.review = review_text.strip()
        review.save()

        # ✅ UPDATE PLACE STATS
        place = review.place

        place.refresh_review_stats()

        messages.success(
            request,
            "✅ Your review has been updated successfully!"
        )

        return redirect(
            'destinations:place_detail',
            destination_id=place.destination.id,
            place_id=review.place.id
        )

    # ✅ DYNAMIC BASE TEMPLATE
    base_template = (
        "admin_app/base.html"
        if request.user.is_staff or request.user.is_superuser
        else "travellers/base.html"
    )

    return render(
        request,
        "destinations/edit_review.html",
        {
            "review": review,
            "base_template": base_template
        }
    )

from django.db.models import Avg

@login_required
def delete_review(request, review_id):

    review = get_object_or_404(
        PlaceReview,
        id=review_id
    )

    # =====================================================
    # PERMISSION CHECK
    # =====================================================

    if (
        review.user != request.user
        and not request.user.is_staff
        and not request.user.is_superuser
    ):

        messages.error(
            request,
            "You don't have permission to delete this review."
        )

        return redirect(
            'destinations:place_detail',
            destination_id=review.place.destination.id,
            place_id=review.place.id
        )

    # =====================================================
    # STORE PLACE BEFORE DELETE
    # =====================================================

    place = review.place

    review.delete()

    # =====================================================
    # REFRESH STATS
    # =====================================================

    place.refresh_review_stats()

    # =====================================================
    # SUCCESS
    # =====================================================

    messages.success(
        request,
        "✅ Your review has been deleted."
    )

    return redirect(
        'destinations:place_detail',
        destination_id=place.destination.id,
        place_id=place.id
    )

@login_required
def delete_place(request, place_id):
    place = get_object_or_404(
        DestinationPlace,
        id=place_id
    )

    # =====================================================
    # PERMISSION CHECK
    # =====================================================

    if (
        request.user != place.created_by
        and not request.user.is_staff
        and not request.user.is_superuser
    ):

        messages.error(
            request,
            "You don't have permission to delete this place."
        )

        return redirect(
            "destinations:place_detail",
            place_id=place.id
        )

    destination_id = place.destination.id

    # =====================================================
    # DELETE PLACE
    # =====================================================

    if request.method == "POST":

        place_name = place.name

        create_audit_log(
            user=request.user,
            action='place_deleted',
            description=f'Deleted place: {place_name}'
        )

        place.delete()

        messages.success(
            request,
            f'🗑️ "{place_name}" deleted successfully!'
        )

        return redirect(
            "destinations:destination_detail",
            destination_id=destination_id
        )

    # =====================================================
    # SAFETY FALLBACK
    # =====================================================

    return redirect(
        "destinations:place_detail",
        destination_id=place.destination.id,
        place_id=place.id
    )

@login_required
def add_destination_review(request, destination_id):

    destination = get_object_or_404(
        Destination,
        id=destination_id
    )

    existing_review = DestinationReview.objects.filter(
        destination=destination,
        user=request.user
    ).first()

    if existing_review:

        messages.warning(
            request,
            "You have already reviewed this destination."
        )

        return redirect(
            "destinations:destination_detail",
            destination_id=destination.id
        )

    if request.method == "POST":

        rating = request.POST.get("rating")
        review_text = request.POST.get("review")

        if not rating or not review_text:

            messages.error(
                request,
                "Please provide both rating and review."
            )

            return redirect(
                "destinations:add_destination_review",
                destination_id=destination.id
            )

        try:

            DestinationReview.objects.create(
                destination=destination,
                user=request.user,
                rating=int(rating),
                review=review_text.strip()
            )

            create_audit_log(
                user=request.user,
                action='destination_review_added',
                description=f'Reviewed destination: {destination.name}'
            )

            destination.refresh_review_stats()

            messages.success(
                request,
                f"✅ Review added for {destination.name}"
            )

            return redirect(
                "destinations:destination_detail",
                destination_id=destination.id
            )

        except Exception as e:

            messages.error(
                request,
                f"Error saving review: {str(e)}"
            )

    base_template = (
        "admin_panel/base.html"
        if request.user.is_staff or request.user.is_superuser
        else "travellers/base.html"
    )

    return render(
        request,
        "destinations/add_destination_review.html",
        {
            "destination": destination,
            "base_template": base_template
        }
    )

@login_required
def edit_destination_review(request, review_id):

    review = get_object_or_404(
        DestinationReview,
        id=review_id
    )

    if review.user != request.user:

        messages.error(
            request,
            "You don't have permission to edit this review."
        )

        return redirect(
            "destinations:destination_detail",
            destination_id=review.destination.id
        )

    if request.method == "POST":

        rating = request.POST.get("rating")
        review_text = request.POST.get("review")

        if not rating or not review_text:

            messages.error(
                request,
                "Please provide both rating and review."
            )

            return redirect(
                "destinations:edit_destination_review",
                review_id=review.id
            )

        review.rating = int(rating)
        review.review = review_text.strip()

        review.save()

        review.destination.refresh_review_stats()

        messages.success(
            request,
            "✅ Review updated successfully."
        )

        return redirect(
            "destinations:destination_detail",
            destination_id=review.destination.id
        )

    base_template = (
        "admin_panel/base.html"
        if request.user.is_staff or request.user.is_superuser
        else "travellers/base.html"
    )

    return render(
        request,
        "destinations/edit_destination_review.html",
        {
            "review": review,
            "destination": review.destination,
            "base_template": base_template
        }
    )


@login_required
def delete_destination_review(request, review_id):

    review = get_object_or_404(
        DestinationReview,
        id=review_id
    )

    if (
        review.user != request.user
        and not request.user.is_staff
        and not request.user.is_superuser
    ):

        messages.error(
            request,
            "You don't have permission to delete this review."
        )

        return redirect(
            "destinations:destination_detail",
            destination_id=review.destination.id
        )

    destination = review.destination

    review.delete()

    destination.refresh_review_stats()

    messages.success(
        request,
        "✅ Review deleted successfully."
    )

    return redirect(
        "destinations:destination_detail",
        destination_id=destination.id
    )

from community.models import Notification

@staff_member_required
def approve_destination(request, destination_id):

    destination = get_object_or_404(
        Destination,
        id=destination_id
    )

    destination.is_approved = True
    destination.save()

    Notification.create_destination_approved_notification(
        destination
    )

    messages.success(
        request,
        f"{destination.name} approved successfully."
    )
    create_audit_log(
        user=request.user,
        action='destination_approved',
        description=f'Approved destination: {destination.name}'
    )

    return redirect(
        "admin_app:admin_approvals"
    )

@staff_member_required
def reject_destination(request, destination_id):

    destination = get_object_or_404(
        Destination,
        id=destination_id
    )

    Notification.create_destination_rejected_notification(
        destination
    )

    create_audit_log(
        user=request.user,
        action='destination_rejected',
        description=f'Rejected destination: {destination.name}'
    )

    destination.delete()

    messages.success(
        request,
        "Destination rejected."
    )

    return redirect(
        "admin_app:admin_approvals"
    )

@staff_member_required
def approve_place(request, place_id):

    place = get_object_or_404(
        DestinationPlace,
        id=place_id
    )

    place.is_approved = True
    place.save()

    Notification.create_place_approved_notification(
        place
    )

    messages.success(
        request,
        f"{place.name} approved successfully."
    )

    create_audit_log(
        user=request.user,
        action='place_approved',
        description=f'Approved place: {place.name}'
    )

    return redirect(
        "admin_app:admin_approvals"
    )

@staff_member_required
def reject_place(request, place_id):

    place = get_object_or_404(
        DestinationPlace,
        id=place_id
    )

    Notification.create_place_rejected_notification(
        place
    )

    create_audit_log(
        user=request.user,
        action='place_rejected',
        description=f'Rejected place: {place.name}'
    )

    place.delete()

    messages.success(
        request,
        "Place rejected."
    )

    return redirect(
        "admin_app:admin_approvals"
    )