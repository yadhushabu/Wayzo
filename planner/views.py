# planner/views.py

from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.http import JsonResponse
from django.conf import settings
import json
from django.contrib.auth.decorators import login_required
from planner.models import SavedItinerary

from .forms import TripForm
from .models import SavedItinerary, TripRequest, Itinerary
from django.views.decorators.http import require_POST
from planner.services.scheduler import (
    smart_schedule,
    get_travel_time
)

from planner.services.itinerary_generator import (
    generator,
    AIItineraryGenerator
)
def recalculate_times(activities):
    base_hour = 9  # start day at 9 AM

    for i, act in enumerate(activities):
        # simple spacing logic (you can improve later with Google Maps travel time)
        hour = base_hour + int(i * 1.5)

        ampm = "AM"
        display_hour = hour

        if hour >= 12:
            ampm = "PM"
            if hour > 12:
                display_hour = hour - 12

        act["time"] = f"{display_hour}:00 {ampm}"

    return activities

# =========================================================
# 🔥 PAGE → PLANNER FORM
# =========================================================

@csrf_protect
def planner(request):

    form = TripForm()

    api_error = None

    # =====================================================
    # 🔥 CHECK API CONFIG
    # =====================================================

    if not getattr(settings, 'SERPAPI_KEY', None):

        api_error = (
            "SerpAPI key is not configured. "
            "Please add it in settings.py"
        )

    return render(
        request,
        'planner/planner_form.html',
        {
            'form': form,
            'api_error': api_error
        }
    )


# =========================================================
# 🔥 GENERATE ITINERARY
# =========================================================

import traceback
import logging

logger = logging.getLogger(__name__)


@csrf_protect
def generate_itinerary(request):

    if request.method != 'POST':
        return redirect('planner')

    itinerary_data = None
    trip_request = None
    api_error = None
    ai_insights = None

    # 🔥 DEBUG TRACKER
    stage = "FORM_VALIDATION"

    try:
        form = TripForm(request.POST)

        if not form.is_valid():
            logger.warning("❌ Form invalid: %s", form.errors)

            messages.error(request, "Please fill all required fields correctly.")
            return render(request, 'planner/planner_form.html', {'form': form})

        stage = "SAVE_TRIP_REQUEST"
        trip_request = form.save()

        logger.info("✅ Trip request saved: %s", trip_request.id)

        stage = "GENERATE_ITINERARY_CALL"

        logger.info(
            "🌍 GENERATOR INPUT | destination=%s | days=%s | interests=%s",
            trip_request.destination,
            trip_request.days,
            trip_request.interests
        )

        itinerary = None

        try:
            itinerary = generator.generate_itinerary(
                destination=trip_request.destination,
                days=trip_request.days,
                interests=trip_request.interests,
                starting_place=trip_request.starting_place,
                ending_place=trip_request.ending_place,
                traveler_name=trip_request.traveler_name,
                traveler_type=trip_request.traveler_type,
                budget=trip_request.budget,
                hotel_type=trip_request.hotel_type,
                hotel_stars=trip_request.hotel_stars,
                food_preference=trip_request.food_preference,
                activity_level=trip_request.activity_level,
                start_date=trip_request.start_date,
                transport_mode=trip_request.transport_mode,
                include_hidden_gems=trip_request.include_hidden_gems,
                include_nightlife=trip_request.include_nightlife,
                include_shopping=trip_request.include_shopping,
                include_local_food=trip_request.include_local_food,
                special_requirements=trip_request.special_requirements,
                user_profile=None
            )

        except Exception as gen_error:
            logger.error("❌ GENERATOR CRASHED at stage=%s", stage)
            logger.error(traceback.format_exc())
            return render(request, 'planner/planner_form.html', {
                'form': TripForm(request.POST),
                'api_error': f"Generator crash: {str(gen_error)}"
            })

        # =====================================================
        # 🔥 HARD SAFETY VALIDATION (IMPROVED)
        # =====================================================

        stage = "VALIDATE_ITINERARY"

        logger.info("📦 OUTPUT TYPE: %s", type(itinerary))
        logger.info("📦 OUTPUT PREVIEW: %s", str(itinerary)[:500])

        if itinerary is None:
            logger.error("❌ ITINERARY IS NONE (generator returned nothing)")
            raise ValueError("Generator returned None")

        if not isinstance(itinerary, dict):
            logger.error("❌ INVALID TYPE: %s", type(itinerary))
            raise TypeError(f"Expected dict, got {type(itinerary)}")

        if not itinerary.get("days"):
            logger.error("❌ EMPTY DAYS BLOCK: %s", itinerary)
            raise ValueError("Itinerary has no 'days'")
        
        saved_itinerary = SavedItinerary.objects.create(
            user=request.user,
            itinerary_json=itinerary,
            destination=trip_request.destination,
            days=trip_request.days,
            title=f"{trip_request.destination} Trip"
        )

        stage = "SAVE_ITINERARY"

        saved_itinerary, created = Itinerary.objects.update_or_create(
            trip_request=trip_request,
            defaults={
                'data': itinerary,
                'summary': f"{trip_request.days}-day trip to {trip_request.destination}",
                'estimated_budget': itinerary.get('estimated_total_budget', 'Not Available'),
            }
        )

        itinerary_data = itinerary

        messages.success(request, "✨ Personalized itinerary generated successfully!")

        stage = "AI_INSIGHTS"

        try:
            all_attractions = []
            all_restaurants = []

            for day in itinerary.get('days', []):

                for activity in day.get('activities', []):

                    if activity.get('time') in ['Breakfast', 'Lunch', 'Dinner']:
                        all_restaurants.append(activity)
                    else:
                        all_attractions.append(activity)

            logger.info(
                "🧠 AI input sizes | attractions=%s restaurants=%s",
                len(all_attractions),
                len(all_restaurants)
            )

            ai_insights = generator.groq.optimize_itinerary(
                destination=trip_request.destination,
                days=trip_request.days,
                interests=trip_request.interests,
                attractions=all_attractions[:20],
                restaurants=all_restaurants[:10],
                hotels=itinerary.get('hotel_recommendations', [])
            )

            itinerary_data['ai_insights'] = ai_insights

        except Exception as ai_error:
            logger.error("⚠️ AI Insights Error: %s", str(ai_error))
            logger.error(traceback.format_exc())

        stage = "RENDER"

        return render(request, 'planner/itinerary.html', {
            'itinerary': itinerary_data,
            'trip': trip_request,
            'ai_insights': ai_insights,
            "saved_itinerary_id": saved_itinerary.id,
            'GOOGLE_API_KEY': settings.GOOGLE_API_KEY,
        })

    except Exception as e:

        logger.error("❌ ERROR STAGE: %s", stage)
        logger.error("❌ ERROR MESSAGE: %s", str(e))
        logger.error("❌ FULL TRACEBACK:\n%s", traceback.format_exc())

        api_error = f"API Error at stage [{stage}]: {str(e)}"

        messages.error(request, api_error)

        return render(request, 'planner/planner_form.html', {
            'form': TripForm(request.POST),
            'api_error': api_error
        })

# =========================================================
# 🔥 AJAX REVIEWS API
# =========================================================

def get_reviews(request):

    place_name = request.GET.get('place')

    destination = request.GET.get('destination')

    lat = request.GET.get('lat')

    lon = request.GET.get('lon')

    if not place_name:

        return JsonResponse({

            'success': False,

            'error': 'Place name required'
        })

    try:

        reviews = generator.get_place_reviews(

            place_name=place_name,

            destination=destination,

            lat=lat,

            lon=lon
        )

        return JsonResponse({

            'success': True,

            'reviews': reviews
        })

    except Exception as e:

        return JsonResponse({

            'success': False,

            'error': str(e)
        })
    


    
from django.http import JsonResponse
from django.conf import settings
import json
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.core.exceptions import ObjectDoesNotExist

from planner.models import Itinerary
from planner.services.scheduler import smart_schedule


@csrf_exempt
@require_POST
def replace_activity(request):
    """
    Replace an activity in the itinerary and reschedule times
    """
    try:
        # Parse the request body
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError as e:
            return JsonResponse({
                "success": False,
                "error": f"Invalid JSON: {str(e)}"
            }, status=400)

        # Extract required fields
        trip_id = data.get("trip_id")
        day_index = data.get("day_index")
        activity_index = data.get("activity_index")
        new_activity = data.get("new_activity")

        # Validate required fields
        if trip_id is None:
            return JsonResponse({
                "success": False,
                "error": "Missing trip_id"
            }, status=400)
        
        if day_index is None:
            return JsonResponse({
                "success": False,
                "error": "Missing day_index"
            }, status=400)
        
        if activity_index is None:
            return JsonResponse({
                "success": False,
                "error": "Missing activity_index"
            }, status=400)
        
        if not new_activity:
            return JsonResponse({
                "success": False,
                "error": "Missing new_activity"
            }, status=400)

        # Convert to integers
        try:
            day_index = int(day_index)
            activity_index = int(activity_index)
            trip_id = int(trip_id)
        except (ValueError, TypeError) as e:
            return JsonResponse({
                "success": False,
                "error": f"Invalid index values: {str(e)}"
            }, status=400)

        # Get the itinerary
        try:
            itinerary_obj = Itinerary.objects.get(trip_request_id=trip_id)
        except ObjectDoesNotExist:
            return JsonResponse({
                "success": False,
                "error": f"Itinerary not found for trip_id: {trip_id}"
            }, status=404)

        itinerary = itinerary_obj.data

        # Validate itinerary structure
        if not isinstance(itinerary, dict):
            return JsonResponse({
                "success": False,
                "error": "Invalid itinerary data structure"
            }, status=500)

        if "days" not in itinerary:
            return JsonResponse({
                "success": False,
                "error": "Itinerary has no days"
            }, status=500)

        if day_index >= len(itinerary["days"]):
            return JsonResponse({
                "success": False,
                "error": f"Day index {day_index} out of range (0-{len(itinerary['days'])-1})"
            }, status=400)

        # Get the day
        day = itinerary["days"][day_index]
        
        if "activities" not in day:
            return JsonResponse({
                "success": False,
                "error": f"Day {day_index} has no activities"
            }, status=500)

        if activity_index >= len(day["activities"]):
            return JsonResponse({
                "success": False,
                "error": f"Activity index {activity_index} out of range (0-{len(day['activities'])-1})"
            }, status=400)

        # Preserve the original activity's type and meal time if applicable
        original_activity = day["activities"][activity_index]
        
        # Don't replace travel blocks
        if original_activity.get("type") == "travel":
            return JsonResponse({
                "success": False,
                "error": "Cannot replace travel blocks directly"
            }, status=400)
        
        # Preserve important fields
        if "type" in original_activity:
            new_activity["type"] = original_activity["type"]
        if original_activity.get("time") in ["Breakfast", "Lunch", "Dinner"]:
            new_activity["time"] = original_activity["time"]
        
        # Ensure required fields
        if "description" not in new_activity or not new_activity["description"]:
            new_activity["description"] = f"Visit {new_activity.get('name', 'this place')} - A wonderful place to explore"
        
        # Replace the activity
        day["activities"][activity_index] = new_activity

        # -----------------------------------
        # SMART RE-SCHEDULING ENGINE
        # -----------------------------------
        try:
            updated_activities = smart_schedule(
                day["activities"],
                start_time=9
            )
        except Exception as e:
            # If smart_schedule fails, just keep original times
            updated_activities = day["activities"]
            print(f"Warning: smart_schedule failed: {e}")

        # IMPORTANT: replace full updated list
        day["activities"] = updated_activities

        # OPTIONAL: rebuild route consistency
        day["route_points"] = [
            {
                "name": a.get("name"),
                "lat": a.get("lat"),
                "lon": a.get("lon"),
                "type": a.get("type"),
                "time": a.get("start_time", a.get("time", ""))
            }
            for a in updated_activities
            if a.get("lat") and a.get("lon")
        ]

        itinerary["days"][day_index] = day

        # Save the updated itinerary
        itinerary_obj.data = itinerary
        itinerary_obj.save()

        # Return updated activities with timing information
        updated_activities_list = []
        for idx, act in enumerate(updated_activities):
            updated_activities_list.append({
                "name": act.get("name", ""),
                "start_time": act.get("start_time", act.get("time", "")),
                "end_time": act.get("end_time", ""),
                "description": act.get("description", "")
            })

        return JsonResponse({
            "success": True,
            "updated_activities": updated_activities_list,
            "message": "Activity updated successfully"
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            "success": False,
            "error": f"Server error: {str(e)}"
        }, status=500)


@csrf_exempt
@require_POST
def save_itinerary(request):

    try:

        data = json.loads(request.body)

        itinerary = data.get("itinerary")

        trip_id = data.get("trip_id")

        if not itinerary:
            return JsonResponse({
                "success": False,
                "error": "No itinerary provided"
            })

        saved = Itinerary.objects.get(
            trip_request_id=trip_id
        )

        saved.data = itinerary

        saved.save()

        return JsonResponse({
            "success": True
        })

    except Exception as e:

        print("❌ SAVE ITINERARY ERROR:", e)

        return JsonResponse({
            "success": False,
            "error": str(e)
        })
    

@csrf_exempt
@require_POST
def replace_hotel(request):
    """
    Replace a hotel in the itinerary
    """
    try:
        # Parse the request body
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError as e:
            return JsonResponse({
                "success": False,
                "error": f"Invalid JSON: {str(e)}"
            }, status=400)

        # Extract required fields
        trip_id = data.get("trip_id")
        day_index = data.get("day_index")
        new_hotel = data.get("new_hotel")

        # Validate required fields
        if trip_id is None:
            return JsonResponse({
                "success": False,
                "error": "Missing trip_id"
            }, status=400)
        
        if day_index is None:
            return JsonResponse({
                "success": False,
                "error": "Missing day_index"
            }, status=400)
        
        if not new_hotel:
            return JsonResponse({
                "success": False,
                "error": "Missing new_hotel"
            }, status=400)

        # Convert to integers
        try:
            day_index = int(day_index)
            trip_id = int(trip_id)
        except (ValueError, TypeError) as e:
            return JsonResponse({
                "success": False,
                "error": f"Invalid index values: {str(e)}"
            }, status=400)

        # Get the itinerary
        try:
            itinerary_obj = Itinerary.objects.get(trip_request_id=trip_id)
        except ObjectDoesNotExist:
            return JsonResponse({
                "success": False,
                "error": f"Itinerary not found for trip_id: {trip_id}"
            }, status=404)

        itinerary = itinerary_obj.data

        # Validate itinerary structure
        if not isinstance(itinerary, dict):
            return JsonResponse({
                "success": False,
                "error": "Invalid itinerary data structure"
            }, status=500)

        if "days" not in itinerary:
            return JsonResponse({
                "success": False,
                "error": "Itinerary has no days"
            }, status=500)

        if day_index >= len(itinerary["days"]):
            return JsonResponse({
                "success": False,
                "error": f"Day index {day_index} out of range (0-{len(itinerary['days'])-1})"
            }, status=400)

        # Replace hotel for the specific day
        itinerary["days"][day_index]["stay"] = new_hotel

        # Save the updated itinerary
        itinerary_obj.data = itinerary
        itinerary_obj.save()

        return JsonResponse({
            "success": True,
            "message": "Hotel updated successfully"
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            "success": False,
            "error": f"Server error: {str(e)}"
        }, status=500)
    

