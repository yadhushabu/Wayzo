from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import json

from destinations.models import Destination
from travellers.models import TravelPlan
from ai_engine.services import generate_smart_itinerary
from restaurants.models import RestaurantProfile
from .models import Itinerary, ItineraryDay, CustomizedItinerary

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from destinations.models import Destination
from travellers.models import TravelPlan
from ai_engine.services import generate_smart_itinerary

@login_required
def generate_itinerary(request, destination_id):
    """Generate itinerary for a destination"""
    
    destination = get_object_or_404(Destination, id=destination_id)
    
    # Debug: Check attractions
    attraction_count = destination.attractions.count()
    print(f"\n{'='*50}")
    print(f"🎯 Destination: {destination.name}")
    print(f"📍 Attractions in DB: {attraction_count}")
    
    if attraction_count == 0:
        messages.error(request, f"No attractions found for {destination.name}. Please add attractions first.")
        return redirect("destination_detail", slug=destination.slug)
    
    # Get travel plan
    travel_plan = TravelPlan.objects.filter(
        user=request.user,
        destination=destination
    ).order_by("-created_at").first()
    
    if not travel_plan:
        messages.warning(request, "Please create a travel plan first.")
        return redirect("create_travel_plan")
    
    # Set defaults if missing
    if not travel_plan.transport_mode:
        travel_plan.transport_mode = "car"
    
    if not travel_plan.start_time:
        from datetime import time
        travel_plan.start_time = time(9, 0)
    
    if not travel_plan.pace:
        travel_plan.pace = "medium"
    
    # Generate itinerary
    try:
        result = generate_smart_itinerary(destination, travel_plan)
        
        if not result.get("days"):
            messages.warning(request, "Could not generate itinerary. Please check your travel plan settings.")
            return redirect("destination_detail", slug=destination.slug)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        messages.error(request, f"Failed to generate itinerary: {str(e)}")
        return redirect("destination_detail", slug=destination.slug)
    
    # Prepare context
    days = result.get("days", [])
    total_activities = sum(day.get("total_activities", 0) for day in days)
    
    context = {
        "destination": destination,
        "travel_plan": travel_plan,
        "days": days,
        "budget": result.get("budget", 0),
        "destination_score": result.get("destination_score", 0),
        "has_itinerary": total_activities > 0,
        "total_days": len(days),
        "total_activities": total_activities,
        "people_count": travel_plan.adults + travel_plan.children,
        "transport_mode": travel_plan.transport_mode,
        "start_date": travel_plan.start_date,
        "end_date": travel_plan.end_date,
    }
    
    return render(request, "itineraries/itinerary_detail.html", context)

@login_required
@require_http_methods(["POST"])
def customize_itinerary(request, itinerary_id):
    """Allow users to customize their itinerary"""
    itinerary = get_object_or_404(Itinerary, id=itinerary_id, user=request.user)
    
    try:
        data = json.loads(request.body)
        
        # Create customized version
        customized = CustomizedItinerary.objects.create(
            original_itinerary=itinerary,
            user=request.user,
            modified_data=data.get("modified_data", {}),
            notes=data.get("notes", "")
        )
        
        return JsonResponse({
            "status": "success",
            "customized_id": customized.id,
            "message": "Itinerary customized successfully!"
        })
    except Exception as e:
        return JsonResponse({
            "status": "error",
            "message": str(e)
        }, status=400)

@login_required
def regenerate_day(request, itinerary_id, day_number):
    """Regenerate a specific day with new preferences"""
    itinerary = get_object_or_404(Itinerary, id=itinerary_id, user=request.user)
    
    # Get user preferences for this day
    preference = request.GET.get('preference', 'balanced')
    
    # Logic to regenerate specific day
    # (Implementation depends on your specific requirements)
    
    return JsonResponse({
        "status": "success",
        "message": f"Day {day_number} regenerated with {preference} preference"
    })

@login_required
def save_itinerary_note(request, itinerary_id):
    """Save user notes on itinerary"""
    if request.method == "POST":
        itinerary = get_object_or_404(Itinerary, id=itinerary_id, user=request.user)
        note = request.POST.get('note', '')
        
        itinerary.notes = note
        itinerary.save()
        
        messages.success(request, "Note saved successfully!")
        return redirect("view_itinerary", itinerary_id=itinerary_id)