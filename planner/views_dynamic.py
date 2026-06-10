from django.http import JsonResponse
from planner.services.itinerary_generator import generator
from planner.models import Itinerary
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import ObjectDoesNotExist
import traceback

def get_alternatives(request):

    # =====================================================
    # GET PARAMS
    # =====================================================

    activity_type = request.GET.get("type", "general")

    lat = request.GET.get("lat")
    lon = request.GET.get("lon")

    destination = request.GET.get("destination", "")

    exclude = request.GET.get("exclude", "")

    print("\n==============================")
    print("🔄 ALTERNATIVE ACTIVITY REQUEST")
    print("==============================")
    print("TYPE:", activity_type)
    print("LAT:", lat)
    print("LON:", lon)
    print("DESTINATION:", destination)
    print("EXCLUDE:", exclude)

    # =====================================================
    # FETCH ALTERNATIVES
    # =====================================================

    alternatives = generator.get_dynamic_alternatives(
        activity_type=activity_type,
        lat=lat,
        lon=lon,
        destination=request.GET.get("destination", "Goa"),
        exclude_name=request.GET.get("exclude", "")
    )

    print(f"✅ Alternatives returned: {len(alternatives)}")

    return JsonResponse({
        "alternatives": alternatives
    })

import json

from django.http import JsonResponse
from django.views.decorators.http import require_POST

from planner.services.scheduler import smart_schedule


@csrf_exempt
@require_POST
def replace_activity(request):
    """
    Replace an activity in the itinerary, reschedule the full day,
    correctly stamp from_place / to_place on every travel block,
    and return the COMPLETE enriched activity list so the frontend
    can do a full re-render without missing any fields.
    """
    try:
        # ── parse body ──────────────────────────────────────────────
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError as e:
            return JsonResponse({"success": False, "error": f"Invalid JSON: {e}"}, status=400)

        trip_id        = data.get("trip_id")
        day_index      = data.get("day_index")
        activity_index = data.get("activity_index")
        new_activity   = data.get("new_activity")

        for field, val in [("trip_id", trip_id), ("day_index", day_index),
                            ("activity_index", activity_index), ("new_activity", new_activity)]:
            if val is None:
                return JsonResponse({"success": False, "error": f"Missing {field}"}, status=400)

        try:
            day_index      = int(day_index)
            activity_index = int(activity_index)
            trip_id        = int(trip_id)
        except (ValueError, TypeError) as e:
            return JsonResponse({"success": False, "error": f"Bad index: {e}"}, status=400)

        # ── load itinerary ──────────────────────────────────────────
        try:
            itinerary_obj = Itinerary.objects.get(trip_request_id=trip_id)
        except ObjectDoesNotExist:
            return JsonResponse({"success": False, "error": f"Itinerary not found for trip_id: {trip_id}"}, status=404)

        itinerary = itinerary_obj.data
        if not isinstance(itinerary, dict) or "days" not in itinerary:
            return JsonResponse({"success": False, "error": "Invalid itinerary structure"}, status=500)

        if day_index >= len(itinerary["days"]):
            return JsonResponse({"success": False, "error": f"Day index {day_index} out of range"}, status=400)

        day = itinerary["days"][day_index]
        activities = day.get("activities", [])

        if activity_index >= len(activities):
            return JsonResponse({"success": False, "error": f"Activity index {activity_index} out of range"}, status=400)

        original = activities[activity_index]

        # Don't replace travel blocks directly
        if original.get("type") == "travel":
            return JsonResponse({"success": False, "error": "Cannot replace travel blocks"}, status=400)

        # ── preserve meal slot + type ───────────────────────────────
        if "type" in original:
            new_activity["type"] = original["type"]
        if original.get("time") in ("Breakfast", "Lunch", "Dinner"):
            new_activity["time"] = original["time"]
        if not new_activity.get("description"):
            new_activity["description"] = (
                f"Visit {new_activity.get('name', 'this place')} — A wonderful place to explore"
            )
        new_activity["changeable"] = True

        # ── swap ────────────────────────────────────────────────────
        activities[activity_index] = new_activity

        # ── reschedule the whole day ────────────────────────────────
        try:
            rescheduled = smart_schedule(activities, start_time=9)
        except Exception as e:
            print(f"Warning: smart_schedule failed: {e}")
            rescheduled = activities

        # ── stamp from_place / to_place on every travel block ───────
        #
        # Build ordered list of NON-travel activity names so we can
        # look up the neighbours of each travel block.
        #
        non_travel_names = [
            a.get("name", "")
            for a in rescheduled
            if a.get("type") != "travel"
        ]

        non_travel_cursor = 0   # how many non-travel activities we've passed

        for act in rescheduled:
            if act.get("type") == "travel":
                # previous non-travel activity
                prev_name = (
                    non_travel_names[non_travel_cursor - 1]
                    if non_travel_cursor > 0
                    else "Starting point"
                )
                # next non-travel activity
                next_name = (
                    non_travel_names[non_travel_cursor]
                    if non_travel_cursor < len(non_travel_names)
                    else "Destination"
                )
                act["from_place"]  = prev_name
                act["to_place"]    = next_name
                act["name"]        = f"Travel from {prev_name} to {next_name}"
                act["description"] = f"🚗 Travelling from {prev_name} to {next_name}"
            else:
                non_travel_cursor += 1

        # ── persist ─────────────────────────────────────────────────
        day["activities"] = rescheduled
        day["route_points"] = [
            {
                "name": a.get("name"),
                "lat":  a.get("lat"),
                "lon":  a.get("lon"),
                "type": a.get("type"),
                "time": a.get("start_time", a.get("time", "")),
            }
            for a in rescheduled
            if a.get("lat") and a.get("lon")
        ]
        itinerary["days"][day_index] = day
        itinerary_obj.data = itinerary
        itinerary_obj.save()

        # ── serialise FULL day for the frontend ─────────────────────
        # Include EVERY field the template/JS needs so the re-render
        # produces exactly the same richness as the first render.
        serialised = []
        for act in rescheduled:
            serialised.append({
                # identity / type
                "type":             act.get("type", "activity"),
                "time":             act.get("time", ""),          # Breakfast/Lunch/Dinner/Travel/etc.
                "changeable":       act.get("changeable", True),
                # display
                "name":             act.get("name", ""),
                "description":      act.get("description", ""),
                # timing
                "start_time":       act.get("start_time", act.get("time", "")),
                "end_time":         act.get("end_time", ""),
                "duration_minutes": act.get("duration_minutes"),
                # location
                "lat":              act.get("lat"),
                "lon":              act.get("lon"),
                "address":          act.get("address", ""),
                # enrichment
                "rating":           act.get("rating"),
                "price_level":      act.get("price_level", ""),
                "image_url":        act.get("image_url", ""),
                # travel-specific
                "from_place":       act.get("from_place", ""),
                "to_place":         act.get("to_place", ""),
            })

        return JsonResponse({
            "success":            True,
            "updated_activities": serialised,
            "message":            "Activity replaced and day fully rescheduled",
        })

    except Exception as e:
        traceback.print_exc()
        return JsonResponse({"success": False, "error": f"Server error: {str(e)}"}, status=500)