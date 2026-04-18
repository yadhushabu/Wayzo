import requests
from django.conf import settings


def get_places_from_opentripmap(destination):
    api_key = settings.OPENTRIPMAP_API_KEY

    try:
        # 🔹 Step 1: Get coordinates
        geo_url = "https://api.opentripmap.com/0.1/en/places/geoname"
        geo_params = {
            "name": destination,
            "apikey": api_key
        }

        geo_res = requests.get(geo_url, params=geo_params).json()

        lat = geo_res.get("lat")
        lon = geo_res.get("lon")

        if not lat or not lon:
            return []

        # 🔹 Step 2: Get places (better filtering)
        places_url = "https://api.opentripmap.com/0.1/en/places/radius"
        params = {
            "radius": 8000,
            "lon": lon,
            "lat": lat,
            "rate": 2,
            "limit": 12,
            "format": "json",
            "apikey": api_key
        }

        places_res = requests.get(places_url, params=params).json()

        places = []

        for p in places_res:
            if p.get("name"):  # skip empty names
                places.append({
                    "name": p.get("name"),
                    "category": p.get("kinds"),
                    "rating": p.get("rate", 0)
                })

        return places[:10]

    except Exception as e:
        print("OpenTripMap Error:", e)
        return []