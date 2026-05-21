from django.http import JsonResponse
from planner.services.itinerary_generator import generator


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