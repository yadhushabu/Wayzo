import requests
from datetime import datetime, timedelta
from django.conf import settings


def get_travel_time(origin_lat, origin_lng, dest_lat, dest_lng, mode="driving"):
    """
    Returns travel time in minutes using Google Distance Matrix API
    """

    if not origin_lat or not origin_lng or not dest_lat or not dest_lng:
        return 20  # fallback

    api_key = getattr(settings, "GOOGLE_API_KEY", None)

    if not api_key:
        return 20  # fallback

    url = (
        "https://maps.googleapis.com/maps/api/distancematrix/json"
        f"?origins={origin_lat},{origin_lng}"
        f"&destinations={dest_lat},{dest_lng}"
        f"&mode={mode}"
        f"&key={api_key}"
    )

    try:
        res = requests.get(url, timeout=5).json()
        seconds = res["rows"][0]["elements"][0]["duration"]["value"]
        return seconds / 60
    except:
        return 20
    

from datetime import datetime

def smart_schedule(activities, start_time=9, buffer_time=10):
    """
    Intelligent itinerary scheduler
    - recalculates activity timing
    - adds travel time
    - avoids hour overflow crash
    - formats proper AM/PM timing
    """

    # IMPORTANT: avoid mutating original list
    activities = [dict(a) for a in activities]

    current_time = start_time * 60  # minutes from midnight

    for i, act in enumerate(activities):

        # ---------------------------------
        # 1. Travel Time
        # ---------------------------------
        travel = 0

        if i > 0:
            prev = activities[i - 1]

            if (
                prev.get("lat")
                and prev.get("lon")
                and act.get("lat")
                and act.get("lon")
            ):
                travel = get_travel_time(
                    prev.get("lat"),
                    prev.get("lon"),
                    act.get("lat"),
                    act.get("lon")
                )

        current_time += travel

        # ---------------------------------
        # 2. Activity Duration
        # ---------------------------------
        duration = act.get("duration")

        if not duration:

            activity_type = (act.get("type") or "").lower()

            if activity_type == "restaurant":
                duration = 60

            elif "beach" in act.get("name", "").lower():
                duration = 120

            elif "fort" in act.get("name", "").lower():
                duration = 90

            elif "waterfall" in act.get("name", "").lower():
                duration = 120

            else:
                duration = 90

        # ---------------------------------
        # 3. START TIME
        # ---------------------------------
        start_hour = int(current_time // 60)
        start_min = int(current_time % 60)

        # FIX: prevent >23 crash
        display_start_hour = start_hour % 24

        start_dt = datetime.strptime("00:00", "%H:%M").replace(
            hour=display_start_hour,
            minute=start_min
        )

        act["start_time"] = start_dt.strftime("%I:%M %p")

        # ---------------------------------
        # 4. END TIME
        # ---------------------------------
        end_total = current_time + duration

        end_hour = int(end_total // 60)
        end_min = int(end_total % 60)

        # FIX: prevent >23 crash
        display_end_hour = end_hour % 24

        end_dt = datetime.strptime("00:00", "%H:%M").replace(
            hour=display_end_hour,
            minute=end_min
        )

        act["end_time"] = end_dt.strftime("%I:%M %p")

        # ---------------------------------
        # 5. DISPLAY LABEL
        # ---------------------------------
        act["time"] = (
            f"{act['start_time']} - {act['end_time']}"
        )

        # ---------------------------------
        # 6. EXTRA METADATA
        # ---------------------------------
        act["travel_time_minutes"] = round(travel)
        act["duration_minutes"] = duration

        # ---------------------------------
        # 7. Advance Timeline
        # ---------------------------------
        current_time = end_total + buffer_time

    return activities