# planner/services/itinerary_generator.py

from datetime import datetime, timedelta
import math
import random
import re
import uuid
from planner.services.user_profile import UserProfile

from rapidfuzz import fuzz

from planner.services.serpapi_service import (
    SerpAPIDestinationService
)

from planner.services.groq_service import (
    groq_optimizer
)

from planner.services.vector_retrieval import (
    PlaceVectorDatabase
)

from planner.services.utils import normalize_place_name, haversine_distance

# =========================================================
# 🔥 AI ITINERARY GENERATOR
# =========================================================

class AIItineraryGenerator:

    def __init__(self, user_profile=None):

        self.serpapi = SerpAPIDestinationService()
        self.groq = groq_optimizer
        self.vector_db = PlaceVectorDatabase()

        self.user_profile = user_profile or {
            "liked_places": [],
            "disliked_places": [],
            "preferred_foods": [],
            "preferred_activities": [],
            "preferred_cuisines": []
        }
    # Add this method at the beginning of your AIItineraryGenerator class


    def _build_schedule(self, places, days, destination, interests):
        """Build day-by-day schedule from places (SAFE + ROBUST)"""

        if not places:
            return {
                "destination": destination,
                "interests": interests,
                "days": []
            }

        interests_lower = (interests or "").lower()

        if 'party' in interests_lower:
            time_slots = ['Afternoon (2:00 PM)', 'Evening (8:00 PM)', 'Late Night (11:00 PM)']
        else:
            time_slots = ['Morning (9:00 AM)', 'Afternoon (1:00 PM)', 'Evening (6:00 PM)']

        categorized = {
            'morning': [],
            'afternoon': [],
            'evening': []
        }

        for place in places:

            if not isinstance(place, dict):
                continue

            name = place.get("name") or place.get("title")
            if not name:
                continue

            place_type = (place.get('type') or '').lower()

            if place_type in ['nature', 'culture', 'history', 'destination', 'beach', 'waterfall', 'park']:
                categorized['morning'].append(place)

            elif place_type in ['food', 'restaurant', 'shopping', 'market']:
                categorized['afternoon'].append(place)

            elif place_type in ['party', 'nightlife', 'bar', 'club']:
                categorized['evening'].append(place)

            else:
                categorized['afternoon'].append(place)

        itinerary = {
            'destination': destination,
            'interests': interests,
            'days': []
        }

        for day in range(days):

            day_schedule = {
                'day': day + 1,
                'theme': self._get_theme(day, interests),
                'activities': []
            }

            # ================= MORNING =================
            if categorized['morning']:
                place = categorized['morning'][day % len(categorized['morning'])]

                day_schedule['activities'].append({
                    "id": str(uuid.uuid4()),   # ✅ FIX
                    "type": place.get("type", "general"),
                    "lat": place.get("lat"),
                    "lon": place.get("lon"),

                    'time': time_slots[0],
                    'name': name,
                    'description': place.get('description', f"Explore {name}"),
                    'duration': self._estimate_duration(place),
                    'rating': place.get('rating', 'N/A'),
                    'image_url': place.get(
                        'thumbnail',
                        f"https://source.unsplash.com/600x400/?{destination},nature"
                    )
                })
            else:
                fallback = self._get_fallback_activity(destination, interests, 'morning')
                fallback["id"] = str(uuid.uuid4())
                fallback["type"] = "fallback"
                day_schedule['activities'].append(fallback)

            # ================= AFTERNOON =================
            if categorized['afternoon']:
                place = categorized['afternoon'][day % len(categorized['afternoon'])]
                name = place.get("name") or place.get("title")

                day_schedule['activities'].append({
                    "id": str(uuid.uuid4()),
                    "type": place.get("type", "general"),
                    "lat": place.get("lat"),
                    "lon": place.get("lon"),

                    'time': time_slots[1],
                    'name': name,
                    'description': place.get('description', f"Experience {name}"),
                    'duration': self._estimate_duration(place),
                    'rating': place.get('rating', 'N/A'),
                    'image_url': place.get(
                        'thumbnail',
                        f"https://source.unsplash.com/600x400/?{destination},food"
                    )
                })
            else:
                fallback = self._get_fallback_activity(destination, interests, 'afternoon')
                fallback["id"] = str(uuid.uuid4())
                fallback["type"] = "fallback"
                day_schedule['activities'].append(fallback)

            # ================= EVENING =================
            if categorized['evening']:
                place = categorized['evening'][day % len(categorized['evening'])]
                name = place.get("name") or place.get("title")

                day_schedule['activities'].append({
                    "id": str(uuid.uuid4()),
                    "type": place.get("type", "general"),
                    "lat": place.get("lat"),
                    "lon": place.get("lon"),

                    'time': time_slots[2],
                    'name': name,
                    'description': place.get('description', f"Enjoy {name}"),
                    'duration': self._estimate_duration(place, is_evening=True),
                    'rating': place.get('rating', 'N/A'),
                    'image_url': place.get(
                        'thumbnail',
                        f"https://source.unsplash.com/600x400/?{destination},nightlife"
                    )
                })
            else:
                fallback = self._get_fallback_activity(destination, interests, 'evening')
                fallback["id"] = str(uuid.uuid4())
                fallback["type"] = "fallback"
                day_schedule['activities'].append(fallback)

            itinerary['days'].append(day_schedule)
            self.enrich_day_with_travel_data(day_schedule)
        return itinerary


    def enrich_day_with_travel_data(self, day_schedule):

        # STEP 1: route order
        for idx, activity in enumerate(day_schedule["activities"]):
            activity["route_order"] = idx

        # STEP 2: travel calculations
        for i in range(len(day_schedule["activities"]) - 1):

            current = day_schedule["activities"][i]
            nxt = day_schedule["activities"][i + 1]

            if (
                current.get("lat")
                and current.get("lon")
                and nxt.get("lat")
                and nxt.get("lon")
            ):

                distance = haversine_distance(
                    current["lat"],
                    current["lon"],
                    nxt["lat"],
                    nxt["lon"]
                )

                travel_minutes = self.estimate_travel_time(
                    current["lat"],
                    current["lon"],
                    nxt["lat"],
                    nxt["lon"],
                    "car"
                )

                current["distance_km"] = round(distance, 1)
                current["travel_time"] = travel_minutes
    

    def safe_get(self, data, *keys, default=None):
        """Safely get nested dictionary values without None errors"""
        current = data
        for key in keys:
            if current is None or not isinstance(current, dict):
                return default
            current = current.get(key)
            if current is None:
                return default
        return current

    def safe_list(self, data):
        """Safely convert None or invalid data to empty list"""
        if data is None:
            print("⚠️ Received None data, returning empty list")
            return []
        if not isinstance(data, list):
            print(f"⚠️ Expected list but got {type(data)}")
            return []
        # Filter out None values and non-dict items
        cleaned = []
        for x in data:
            if x is None:
                continue
            if not isinstance(x, dict):
                continue
            cleaned.append(x)
        return cleaned
    




    def apply_transition(self, current_time, current_location, next_place, transport_mode):
        """Safely apply travel time between places"""

        # ---------------- SAFETY CHECKS ----------------
        if not current_location or not next_place:
            return current_time, 0

        curr_lat = current_location.get("lat")
        curr_lon = current_location.get("lon")
        next_lat = next_place.get("lat")
        next_lon = next_place.get("lon")

        # If any coordinate missing → skip travel calculation
        if None in [curr_lat, curr_lon, next_lat, next_lon]:
            return current_time, 0

        # Ensure numeric values
        try:
            curr_lat = float(curr_lat)
            curr_lon = float(curr_lon)
            next_lat = float(next_lat)
            next_lon = float(next_lon)
        except (TypeError, ValueError):
            return current_time, 0

        # ---------------- TRAVEL TIME ----------------
        travel_minutes = self.estimate_travel_time(
            curr_lat,
            curr_lon,
            next_lat,
            next_lon,
            transport_mode
        )

        # Safety fallback
        if travel_minutes is None or travel_minutes < 0:
            travel_minutes = 0

        # ---------------- TIME UPDATE ----------------
        updated_time = current_time + timedelta(minutes=travel_minutes)

        return updated_time, travel_minutes
    

    def get_attractions_by_interest(self, destination, interest, limit=10):

        params = {
            "engine": "google_maps",
            "q": f"{interest} in {destination}",
            "type": "search",
            "api_key": self.api_key
        }

        results = self._safe_search(params)

        places = results.get("local_results", [])

        if isinstance(places, dict):
            places = places.get("places", [])
        elif not isinstance(places, list):
            places = []

        output = []

        for place in places[:limit]:

            if not isinstance(place, dict):
                continue

            gps = place.get("gps_coordinates") or {}

            output.append({
                "name": place.get("title"),
                "rating": place.get("rating"),
                "reviews": place.get("reviews"),
                "address": place.get("address"),
                "thumbnail": place.get("thumbnail"),
                "lat": gps.get("latitude"),
                "lon": gps.get("longitude"),
                "type": interest
            })

        return output   # ✅ FIXED (moved outside loop)


    def build_day_route(self, places, day_index, days, start_location=None):

        # split places evenly per day first
        chunk_size = max(1, len(places) // days)

        start = day_index * chunk_size
        end = start + chunk_size

        day_places = places[start:end]

        return self.build_route(day_places, start_location)
    
    def get_route_nearby_restaurants(self, restaurants, route):

        if not route:
            return restaurants[:3]

        center = route[0]

        nearby = self.get_nearby_places(
            restaurants,
            center["lat"],
            center["lon"],
            max_km=4
        )

        return nearby[:3]

    def get_route_hotel(self, hotels, route):

        if not route:
            return hotels[0]

        end = route[-1]

        nearby = self.get_nearby_places(
            hotels,
            end["lat"],
            end["lon"],
            max_km=6
        )

        return nearby[0] if nearby else hotels[0]

    # =====================================================
    # 🚗 TRAVEL TIME ESTIMATION
    # =====================================================
    def estimate_travel_time(self, lat1, lon1, lat2, lon2, mode="car"):

        if not lat1 or not lon1 or not lat2 or not lon2:
            return 0

        distance = haversine_distance(lat1, lon1, lat2, lon2)

        # average speeds (km/h)
        speeds = {
            "walk": 5,
            "bike": 12,
            "car": 35,
            "auto": 25,
            "mixed": 30
        }

        speed = speeds.get(mode, 30)

        return int((distance / speed) * 60)  # minutes

    def add_travel_time(
        self,
        day_plan,
        current_time,
        current_location,
        next_place,
        transport_mode
    ):

        # =====================================================
        # 🔥 SAFE VALIDATION FIRST (NO .get() BEFORE THIS)
        # =====================================================

        if not current_location or not next_place:
            return current_time, None

        if not isinstance(current_location, dict) or not isinstance(next_place, dict):
            return current_time, None

        lat1 = current_location.get("lat")
        lon1 = current_location.get("lon")
        lat2 = next_place.get("lat")
        lon2 = next_place.get("lon")

        if not lat1 or not lon1 or not lat2 or not lon2:
            return current_time, None

        # =====================================================
        # 🚗 TRAVEL TIME CALCULATION
        # =====================================================

        travel_minutes = self.estimate_travel_time(
            lat1,
            lon1,
            lat2,
            lon2,
            transport_mode
        )

        # =====================================================
        # 🧭 BUILD TRAVEL BLOCK
        # =====================================================

        travel_block = None

        if travel_minutes > 0:

            travel_block = {
                "id": str(uuid.uuid4()),
                "changeable": False,
                "time": "Travel",
                "name": f"Travel to {next_place.get('name', 'Destination')}",
                "type": "travel",

                "start_time": self.format_time(current_time),
                "end_time": self.format_time(
                    current_time + timedelta(minutes=travel_minutes)
                ),

                "duration_minutes": travel_minutes,

                # 🔥 IMPORTANT (for map + dynamic updates)
                "lat": lat2,
                "lon": lon2,

                "description": f"{transport_mode.title()} travel for {travel_minutes} mins"
            }

            day_plan["activities"].append(travel_block)

            current_time += timedelta(minutes=travel_minutes)

        return current_time, travel_block

    # =====================================================
    # 🔥 DISTANCE FILTER (ADD HERE)
    # =====================================================
    def get_nearby_places(self, places, lat, lon, max_km=5):

        if not lat or not lon:
            return places

        nearby = []

        for p in places:

            if not p.get("lat") or not p.get("lon"):
                continue

            dist = haversine_distance(
                lat, lon,
                p["lat"], p["lon"]
            )

            if dist <= max_km:
                nearby.append((dist, p))

        nearby.sort(key=lambda x: x[0])

        return [p for _, p in nearby]
    
    # =====================================================
    # 🔥 ROUTE CENTER CALCULATION
    # =====================================================
    def get_route_center(self, route):

        if not route or not isinstance(route, list):
            return None

        lat_sum = 0
        lon_sum = 0
        count = 0

        for r in route:
            if r.get("lat") and r.get("lon"):
                lat_sum += r["lat"]
                lon_sum += r["lon"]
                count += 1

        if count == 0:
            return None

        return {
            "lat": lat_sum / count,
            "lon": lon_sum / count
        }

    # =====================================================
    # 🔥 NEARBY HOTEL PICKER
    # =====================================================

    def pick_nearby_hotel(self, hotels, current_location):
        """Safely pick a nearby hotel"""
        hotels = self.safe_list(hotels)
        
        if not hotels:
            print("⚠️ No hotels available - returning None")
            return None
        
        if not current_location or not current_location.get("lat") or not current_location.get("lon"):
            print(f"📍 No location data, returning first hotel: {hotels[0].get('name')}")
            return hotels[0]
        
        nearby = self.get_nearby_places(
            hotels,
            current_location.get("lat"),
            current_location.get("lon"),
            max_km=8
        )
        
        result = nearby[0] if nearby else hotels[0]
        print(f"🏨 Selected hotel: {result.get('name')}")
        return result
    

    # =====================================================
    # 🔥 DYNAMIC ALTERNATIVES
    # =====================================================

    def get_dynamic_alternatives(
        self,
        activity_type,
        lat=None,
        lon=None,
        destination="Goa",
        exclude_name=""
    ):

        print("\n==============================")
        print("🔄 DYNAMIC ALTERNATIVES")
        print("==============================")
        print("TYPE:", activity_type)
        print("LAT:", lat)
        print("LON:", lon)
        print("DESTINATION:", destination)

        activity_type = (activity_type or "").lower()

        alternatives = []

        # =====================================================
        # SAFE COORDS
        # =====================================================

        try:
            lat = float(lat) if lat else None
            lon = float(lon) if lon else None
        except:
            lat = None
            lon = None

        try:

            # =================================================
            # 🍳 BREAKFAST
            # =================================================

            if "breakfast" in activity_type:

                alternatives.extend(
                    self.serpapi.get_restaurants(
                        destination,
                        "breakfast",
                        limit=12
                    )
                )

            # =================================================
            # 🍽️ LUNCH
            # =================================================

            elif "lunch" in activity_type:

                alternatives.extend(
                    self.serpapi.get_restaurants(
                        destination,
                        "lunch",
                        limit=12
                    )
                )

            # =================================================
            # 🍷 DINNER
            # =================================================

            elif "dinner" in activity_type:

                alternatives.extend(
                    self.serpapi.get_restaurants(
                        destination,
                        "dinner",
                        limit=12
                    )
                )

            # =================================================
            # 🏨 HOTELS
            # =================================================

            elif "hotel" in activity_type or "stay" in activity_type:

                alternatives.extend(
                    self.serpapi.get_hotels(
                        destination,
                        limit=12
                    )
                )

            # =================================================
            # 🌴 BEACHES
            # =================================================

            elif "beach" in activity_type:

                alternatives.extend(
                    self.serpapi.get_attractions_by_interest(
                        destination,
                        "best beaches",
                        limit=15
                    )
                )

                alternatives.extend(
                    self.serpapi.get_attractions_by_interest(
                        destination,
                        "sunset beaches",
                        limit=10
                    )
                )

            # =================================================
            # 🌙 NIGHTLIFE
            # =================================================

            elif "night" in activity_type or "party" in activity_type:

                alternatives.extend(
                    self.serpapi.get_attractions_by_interest(
                        destination,
                        "nightlife clubs",
                        limit=12
                    )
                )

                alternatives.extend(
                    self.serpapi.get_attractions_by_interest(
                        destination,
                        "bars pubs rooftop",
                        limit=10
                    )
                )

            # =================================================
            # 🛍️ SHOPPING
            # =================================================

            elif "shopping" in activity_type:

                alternatives.extend(
                    self.serpapi.get_attractions_by_interest(
                        destination,
                        "shopping markets",
                        limit=12
                    )
                )

            # =================================================
            # 🌄 GENERAL TOURISM
            # =================================================

            else:

                search_queries = [
                    "top tourist attractions",
                    "must visit places",
                    "iconic landmarks",
                    "hidden gems",
                    "famous places"
                ]

                for query in search_queries:

                    places = self.serpapi.get_attractions_by_interest(
                        destination,
                        query,
                        limit=6
                    )

                    alternatives.extend(places)

            # =================================================
            # CLEAN + REMOVE DUPLICATES
            # =================================================

            cleaned = []
            seen = set()

            for place in alternatives:

                if not isinstance(place, dict):
                    continue

                name = place.get("name")

                if not name:
                    continue

                normalized = normalize_place_name(
                    name,
                    destination
                )

                # skip current activity
                if exclude_name:

                    ex = normalize_place_name(
                        exclude_name,
                        destination
                    )

                    if normalized == ex:
                        continue

                if normalized in seen:
                    continue

                seen.add(normalized)

                cleaned.append({
                    "name": name,
                    "rating": place.get("rating"),
                    "reviews": place.get("reviews"),
                    "address": place.get("address"),
                    "thumbnail": place.get("thumbnail"),
                    "lat": place.get("lat"),
                    "lon": place.get("lon"),
                    "type": place.get("type", activity_type)
                })

            print(f"✅ FINAL ALTERNATIVES: {len(cleaned)}")

            return cleaned[:20]

        except Exception as e:

            print("❌ Alternative fetch failed:", str(e))

            return []


    # =========================================================
    # 🧠 SMART TIME-BASED ALTERNATIVES
    # =========================================================

    def get_smart_alternatives(
        self,
        activity_type,
        lat,
        lon,
        current_time,
        destination="Goa"
    ):

        try:
            hour = current_time.hour
        except:
            hour = 12

        activity_type = (activity_type or "").lower()

        # =====================================================
        # MORNING
        # =====================================================

        if 5 <= hour < 11:

            if "breakfast" in activity_type:

                return self.get_dynamic_alternatives(
                    "breakfast",
                    lat,
                    lon,
                    destination
                )

            return self.get_dynamic_alternatives(
                "nature",
                lat,
                lon,
                destination
            )

        # =====================================================
        # AFTERNOON
        # =====================================================

        elif 11 <= hour < 17:

            if "lunch" in activity_type:

                return self.get_dynamic_alternatives(
                    "lunch",
                    lat,
                    lon,
                    destination
                )

            return self.get_dynamic_alternatives(
                "shopping",
                lat,
                lon,
                destination
            )

        # =====================================================
        # EVENING
        # =====================================================

        elif 17 <= hour < 21:

            return self.get_dynamic_alternatives(
                "beach",
                lat,
                lon,
                destination
            )

        # =====================================================
        # NIGHT
        # =====================================================

        return self.get_dynamic_alternatives(
            "nightlife",
            lat,
            lon,
            destination
        )

    def recalculate_day(self, day_plan, transport_mode="mixed"):

        if not day_plan or "activities" not in day_plan:
            return day_plan

        activities = day_plan["activities"]

        current_time = self.parse_time("08:00 AM")
        current_location = None

        updated = []
        route_points = []

        for i, activity in enumerate(activities):

            if activity.get("type") == "travel":
                continue

            lat = activity.get("lat")
            lon = activity.get("lon")

            # =================================================
            # 🚗 TRAVEL BLOCK
            # =================================================

            if current_location and lat and lon:

                current_time, travel_min = self.apply_transition(
                    current_time,
                    current_location,
                    activity,
                    transport_mode
                )

                updated.append({
                    "time": "Travel",
                    "name": "Travel Time",
                    "type": "travel",
                    "start_time": self.format_time(
                        current_time - timedelta(minutes=travel_min)
                    ),
                    "end_time": self.format_time(current_time),
                    "duration_minutes": travel_min
                })

            # =================================================
            # 📍 ACTIVITY TIMING (FIXED)
            # =================================================

            start_time = current_time

            duration = self.estimate_visit_duration(activity)

            end_time = current_time + timedelta(minutes=duration)

            activity["start_time"] = self.format_time(start_time)
            activity["end_time"] = self.format_time(end_time)

            # 🔥 CRITICAL FIX: keep "time" in sync for frontend
            activity["time"] = activity["start_time"]

            updated.append(activity)

            # update time AFTER activity
            current_time = end_time

            # add buffer for realism (IMPORTANT)
            current_time += timedelta(minutes=10)

            # =================================================
            # 📌 LOCATION UPDATE
            # =================================================

            current_location = {"lat": lat, "lon": lon}

            if lat and lon:
                route_points.append({
                    "name": activity.get("name"),
                    "lat": lat,
                    "lon": lon,
                    "type": activity.get("type"),
                    "time": activity.get("time")
                })

        day_plan["activities"] = updated
        day_plan["route_points"] = route_points

        return day_plan
    
    def parse_time(self, time_str):

        try:
            return datetime.strptime(time_str, "%I:%M %p")
        except:
            return datetime.strptime("08:00 AM", "%I:%M %p")

    # =====================================================
    # 🔥 CURRENT SLOT
    # =====================================================

    def get_current_slot(self, current_time):

        hour = current_time.hour

        if 5 <= hour < 11:
            return "morning"

        elif 11 <= hour < 17:
            return "afternoon"

        elif 17 <= hour < 21:
            return "evening"

        return "night"


    def pick_nearby_restaurant(self, restaurants, current_location):

        restaurants = self.safe_list(restaurants)

        if not restaurants:
            print("⚠️ No restaurants available")
            return None

        if (
            not current_location
            or not current_location.get("lat")
            or not current_location.get("lon")
        ):
            result = random.choice(restaurants)

            print(
                f"📍 No location data, random restaurant: {result.get('name')}"
            )

            return result

        nearby = self.get_nearby_places(
            restaurants,
            current_location["lat"],
            current_location["lon"],
            max_km=5
        )

        candidates = nearby if nearby else restaurants

        result = random.choice(candidates)

        print(
            f"🍽️ Selected restaurant: {result.get('name')}"
        )

        return result
    
    def cluster_places(self, places, radius_km=8):

        clusters = []

        for place in places:

            placed = False

            for cluster in clusters:

                center = cluster[0]

                dist = haversine_distance(
                    center["lat"], center["lon"],
                    place["lat"], place["lon"]
                )

                if dist <= radius_km:
                    cluster.append(place)
                    placed = True
                    break

            if not placed:
                clusters.append([place])

        return clusters

    # =====================================================
    # 🔥 PLACE CLASSIFICATION
    # =====================================================

    def classify_place(self, place):

        name = (
            place.get("name") or ""
        ).lower()

        nightlife_keywords = [

            "club",
            "pub",
            "bar",
            "rooftop",
            "lounge",
            "nightclub",
            "disco",
            "dj",
            "party",
            "casino",
            "music",
            "live music",
            "cocktail",
            "brewery",
            "cafe mambo",
            "titos",
            "curlies",
            "shack"
        ]

        beach_keywords = [
            "beach",
            "coast",
            "shore",
            "bay"
        ]

        shopping_keywords = [
            "market",
            "mall",
            "shopping",
            "bazaar"
        ]

        nature_keywords = [
            "waterfall",
            "falls",
            "park",
            "lake",
            "sanctuary",
            "forest"
        ]

        history_keywords = [
            "fort",
            "museum",
            "palace",
            "church",
            "temple"
        ]

        if any(k in name for k in beach_keywords):
            return "beach"

        if any(k in name for k in nightlife_keywords):
            return "nightlife"

        if any(k in name for k in shopping_keywords):
            return "shopping"

        if any(k in name for k in nature_keywords):
            return "nature"

        if any(k in name for k in history_keywords):
            return "history"

        return "general"

    # =====================================================
    # 🔥 OPENING HOURS
    # =====================================================

    def get_place_opening_hours(self, place):

        ptype = self.classify_place(place)

        if ptype == "nightlife":
            return (18, 3)

        if ptype == "beach":
            return (5, 20)

        if ptype == "nature":
            return (6, 18)

        return (8, 20)

    # =====================================================
    # 🔥 BEST VISIT TIME
    # =====================================================

    def get_best_visit_time(self, place):

        ptype = self.classify_place(place)

        name = (
            place.get("name") or ""
        ).lower()

        # =================================================
        # 🌴 BEACHES
        # =================================================

        if ptype == "beach":

            sunset_keywords = [
                "baga",
                "calangute",
                "candolim",
                "vagator",
                "palolem",
                "anjuna"
            ]

            if any(k in name for k in sunset_keywords):
                return "evening"

            return "afternoon"

        # =================================================
        # 🌃 NIGHTLIFE
        # =================================================

        if ptype == "nightlife":
            return "night"

        # =================================================
        # 🌳 NATURE
        # =================================================

        if ptype == "nature":
            return "morning"

        # =================================================
        # 🏰 HISTORY
        # =================================================

        if ptype == "history":
            return "morning"

        # =================================================
        # 🛍️ SHOPPING
        # =================================================

        if ptype == "shopping":
            return "evening"

        return "afternoon"

    # =====================================================
    # 🔥 VISIT DURATION
    # =====================================================

    def estimate_visit_duration(self, place):

        ptype = self.classify_place(place)

        if ptype == "beach":
            return 180

        if ptype == "nightlife":
            return 120

        if ptype == "nature":
            return 150

        if ptype == "history":
            return 120

        return 90

    # =====================================================
    # 🔥 FORMAT TIME
    # =====================================================

    def format_time(self, dt):

        return dt.strftime("%I:%M %p")
    
    # =====================================================
    # 🔥 UNIVERSAL REGION CLUSTERING
    # =====================================================

    def get_region(self, lat, lon):

        try:

            lat = float(lat)
            lon = float(lon)

            # ============================================
            # 🔥 CREATE GEO GRID
            # ============================================

            # ~10–15 km clustering
            lat_bucket = round(lat * 10) / 10
            lon_bucket = round(lon * 10) / 10

            return f"{lat_bucket}_{lon_bucket}"

        except:

            return "unknown"

    # =====================================================
    # 🔥 FORMAT PLACE
    # =====================================================

    def format_place(
        self,
        place,
        label,
        is_hotel=False
    ):

        return {

            # 🔥 UNIQUE ID
            "id": str(uuid.uuid4()),
            "changeable": True, 

            "time": label,

            "name": place.get("name"),

            "rating": place.get("rating"),

            "reviews": place.get("reviews"),

            "price_level": place.get(
                "price_level"
            ),

            "address": place.get(
                "address"
            ),

            "image_url": (
                place.get("thumbnail")
                or f"https://source.unsplash.com/featured/600x400/?{place.get('name','travel')}"
            ),

            "lat": place.get("lat"),

            "lon": place.get("lon"),

            # 🔥 IMPORTANT FOR DYNAMIC SYSTEM
            "raw_place": place,

            # 🔥 CHANGEABLE
            "changeable": True,

            "type": (
                "hotel"
                if is_hotel
                else self.classify_place(place)
            )
        }

    # =====================================================
    # 🔥 FETCH MUST VISITS
    # =====================================================

    def get_must_visit_places(
        self,
        destination
    ):

        queries = [

            "top tourist attractions",
            "must visit places",
            "iconic landmarks",
            "famous places",
            "best beaches",
            "best sunset beaches",
            "hidden gems",
        ]

        results = []

        for q in queries:

            try:

                data = (
                    self.serpapi
                    .get_attractions_by_interest(
                        destination,
                        q,
                        limit=12
                    )
                )

                print(f"📍 {q} fetched:", len(data))

                results.extend(self.safe_list(data))

            except Exception as e:

                print("❌ Error:", e)

        return results

    # =====================================================
    # 🔥 SCORE PLACE
    # =====================================================

    def score_place(
            self,
            place,
            interest_list,
            include_nightlife=False,
            include_shopping=False,
            include_hidden_gems=True,
            must_visit_names=None,
            destination=""
        ):

        score = 0

        name = normalize_place_name(
            place.get("name", ""),
            destination
        )

        ptype = self.classify_place(place)

        user_profile = self.user_profile or {}

        liked_places = user_profile.get("liked_places", [])
        disliked_places = user_profile.get("disliked_places", [])

        if name in liked_places:
            score += 10

        if name in disliked_places:
            score -= 20

        # ⭐ MUST VISIT BOOST
        if must_visit_names and name in must_visit_names:
            score += 300

        # ⭐ RATINGS
        try:
            score += float(place.get("rating") or 0) * 10
        except:
            pass

        # ⭐ REVIEWS
        try:
            reviews = int(place.get("reviews") or 0)
            score += min(reviews / 500, 70)
        except:
            pass

        # 🌊 INTEREST BOOST
        if "beach" in interest_list and ptype == "beach":
            score += 450

        if include_nightlife and ptype == "nightlife":
            score += 250

        if include_shopping and ptype == "shopping":
            score += 150

        # 💎 HIDDEN GEMS
        if include_hidden_gems and place.get("type") == "hidden_gem":
            score += 80

        # 🎯 TEXT MATCH INTERESTS
        for i in interest_list:
            if i in name:
                score += 120

        # ❤️ PERSONAL FOOD / ACTIVITY MATCH BOOST
        for food in user_profile.get("preferred_foods", []):
            if food in name:
                score += 200

        for fav in user_profile.get("favorite_activity_types", []):
            if fav in ptype:
                score += 150

        # 🚶 WALKING PREFERENCE (FIXED)
        if user_profile.get("walking_preference") == "low":
            if "far" in (place.get("distance_tag") or ""):
                score -= 100

        return score

    # =====================================================
    # 🔥 SELECT BEST PLACE (DISTANCE OPTIMIZED)
    # =====================================================

    def select_best_place(
        self,
        places,
        current_time,
        used_places,
        must_visit_names,
        destination="",
        preferred_types=None,
        skipped_places=None,
        current_location=None,
        ending_location=None,
        day_region=None,
    ):


        if skipped_places is None:
            skipped_places = []

        current_slot = self.get_current_slot(
            current_time
        )

        best_place = None

        best_score = -999999

        for place in places:

            name = place.get("name") or place.get("title")

            if not name:
                continue

            if name in used_places:
                continue

            if name in skipped_places:
                continue

            if not place.get("lat"):
                continue

            if not place.get("lon"):
                continue

            place_type = self.classify_place(place)

            score = 0

            if day_region:

                if place.get("region") == day_region:
                    score += 220
                else:
                    score -= 180

            normalized = normalize_place_name(
                name,
                destination
            )


            # ============================================
            # 🔥 MUST VISIT BOOST
            # ============================================

            if normalized in must_visit_names:
                score += 250

            # ============================================
            # 🔥 PREFERRED TYPE BOOST
            # ============================================

            if preferred_types:

                for pref in preferred_types:

                    pref = pref.lower()

                    if pref in name.lower():
                        score += 140

                    if pref == place_type:
                        score += 120

            # ============================================
            # 🔥 TIME MATCH BOOST
            # ============================================

            preferred_time = self.get_best_visit_time(
                place
            )

            if preferred_time == current_slot:
                score += 120

            # ============================================
            # 🔥 RATINGS
            # ============================================

            try:
                score += (
                    float(place.get("rating", 0))
                    * 8
                )
            except:
                pass

            # ============================================
            # 🔥 REVIEWS
            # ============================================

            try:

                reviews = int(
                    place.get("reviews", 0)
                )

                score += min(reviews / 400, 60)

            except:
                pass

            # ============================================
            # 🔥 DISTANCE LOGIC
            # ============================================

            # ============================================
            # 🔥 SAME REGION BOOST
            # ============================================

            if current_location:

                distance = haversine_distance(

                    current_location["lat"],
                    current_location["lon"],

                    place.get("lat"),
                    place.get("lon")
                )

                # HUGE PENALTY FOR FAR PLACES
                score -= distance * 22


                # ============================================
                # 🔥 END DESTINATION OPTIMIZATION
                # ============================================

                if ending_location:

                    try:

                        end_distance = haversine_distance(

                            place.get("lat"),
                            place.get("lon"),

                            ending_location.get("lat"),
                            ending_location.get("lon")
                        )

                        # encourage route towards ending point
                        score -= end_distance * 4

                    except:
                        pass



                # NEARBY BONUS
                if distance < 5:
                    score += 120

                elif distance < 10:
                    score += 70

                elif distance < 20:
                    score += 30


            # ============================================
            # 🔥 PICK BEST
            # ============================================

            if score > best_score:

                best_score = score
                best_place = place

        return best_place


    # =====================================================
    # 🔥 RESOLVE PLACE
    # =====================================================

    def resolve_location(self, location_name):

        if not location_name:
            return None

        try:

            results = self.serpapi.get_attractions_by_interest(
                location_name,
                "",
                limit=1
            )

            if results:

                return results[0]

        except Exception as e:

            print("Location resolve error:", e)

        return None
    
    # =====================================================
    # 🔥 UNIVERSAL GEO RESOLVER
    # =====================================================

    def resolve_exact_location(self, query):

        if not query:
            return None

        try:
            results = self.serpapi.get_attractions_by_interest(
                query,
                "",
                limit=1
            )

            results = self.safe_list(results)

            if results:
                return results[0]

        except Exception as e:
            print("Exact location resolve error:", e)

        return None


    # =====================================================
    # 🔥 GENERATE ITINERARY
    # =====================================================

    def generate_itinerary(

        self,

        destination,
        days,
        interests,

        starting_place=None,
        ending_place=None,

        traveler_name=None,
        traveler_type='solo',

        budget='mid_range',

        hotel_type='hotel',
        hotel_stars=4,

        food_preference='any',

        activity_level='moderate',

        start_date=None,

        transport_mode='mixed',

        include_hidden_gems=True,
        include_nightlife=False,
        include_shopping=False,
        include_local_food=True,

        special_requirements=None,
        user_profile=None
    ):
        self.user_profile = user_profile

        print(
            f"🌍 Generating itinerary for {destination}"
        )

        interest_list = [

            i.strip().lower()
            for i in interests.split(",")
        ]


        # =================================================
        # 🔥 RESOLVE START & END LOCATIONS
        # =================================================

        resolved_start = None
        resolved_end = None

        if starting_place:

            resolved_start = self.resolve_exact_location(starting_place) or {}


        if ending_place:

            resolved_end = self.resolve_exact_location(
    ending_place
)


        # =================================================
        # 🔥 FETCH PLACES
        # =================================================

        all_places = []

        must_visit = self.get_must_visit_places(
            destination
        )

        all_places.extend(self.safe_list(must_visit))

        for interest in interest_list:

            try:

                data = (
                    self.serpapi
                    .get_attractions_by_interest(
                        destination,
                        interest,
                        limit=20
                    )
                )

                all_places.extend(self.safe_list(data))

            except:
                pass

        # NIGHTLIFE
        nightlife_places = []

        if include_nightlife:

            try:

                nightlife_places = (
                    self.serpapi
                    .get_attractions_by_interest(
                        destination,
                        "best nightlife clubs rooftop bars live music beach clubs open late",
                        limit=25
                    )
                )

                nightlife_places = [

                    p for p in nightlife_places

                    if any(

                        k in (p.get("name") or "").lower()

                        for k in [

                            "club",
                            "bar",
                            "pub",
                            "rooftop",
                            "lounge",
                            "nightclub",
                            "music",
                            "party",
                            "casino",
                            "brewery",
                            "cocktail"
                        ]
                    )
                ]

                all_places.extend(self.safe_list(nightlife_places))

            except:
                pass

        # SHOPPING
        if include_shopping:

            try:

                shopping = (
                    self.serpapi
                    .get_attractions_by_interest(
                        destination,
                        "shopping markets malls",
                        limit=15
                    )
                )

                all_places.extend(self.safe_list(shopping))

            except:
                pass

        # =================================================
        # 🔥 FILTER VALID
        # =================================================

        valid_places = []

        for p in all_places:

            if (
                p.get("name")
                and p.get("lat")
                and p.get("lon")
            ):

                valid_places.append(p)

        # =================================================
        # 🔥 DEDUP
        # =================================================

        unique = []

        seen = []

        for p in valid_places:

            normalized = normalize_place_name(
                p.get("name"),
                destination
            )

            duplicate = False

            for s in seen:

                if fuzz.ratio(
                    normalized,
                    s
                ) > 85:

                    duplicate = True
                    break

            if not duplicate:

                seen.append(normalized)

                unique.append(p)
        
        for p in unique:

            p["region"] = self.get_region(
                p.get("lat"),
                p.get("lon")
            )

        # =================================================
        # 🔥 MUST VISIT SET
        # =================================================

        must_visit_names = set([

            normalize_place_name(
                m.get("name"),
                destination
            )

            for m in must_visit
        ])


        # =================================================
        # 🔥 SORT
        # =================================================

        unique = sorted(
            unique,
            key=lambda p: self.score_place(
                p,
                interest_list,
                include_nightlife,
                include_shopping,
                include_hidden_gems,
                must_visit_names,
                destination
            ),
            reverse=True
        )
        
        # =================================================
        # 🔥 RESTAURANTS
        # =================================================

        breakfast = self.serpapi.get_restaurants(
            destination,
            "breakfast",
            limit=10
        )


        lunch = self.serpapi.get_restaurants(
            destination,
            "lunch",
            limit=10
        )


        dinner = self.serpapi.get_restaurants(
            destination,
            "dinner",
            limit=10
        )


        # =================================================
        # 🔥 HOTELS
        # =================================================

        hotels = self.serpapi.get_hotels(
            destination,
            limit=10
        )

        # =================================================
        # 🔥 SAFETY CHECK - Ensure lists are not None
        # =================================================

        breakfast = self.safe_list(breakfast)
        lunch = self.safe_list(lunch)
        dinner = self.safe_list(dinner)
        hotels = self.safe_list(hotels)

        print(f"✅ Breakfast spots: {len(breakfast)}")
        print(f"✅ Lunch spots: {len(lunch)}")
        print(f"✅ Dinner spots: {len(dinner)}")
        print(f"✅ Hotels: {len(hotels)}")

        # If any are empty, create fallback data
        if not breakfast:
            breakfast = [{
                "name": f"Popular Breakfast Cafe in {destination}",
                "lat": None,
                "lon": None,
                "rating": 4.0,
                "reviews": 100,
                "price_level": "₹₹",
                "address": f"Near {destination} City Center",
                "thumbnail": f"https://source.unsplash.com/featured/600x400/?breakfast,cafe,{destination}"
            }]
            print(f"⚠️ Created fallback breakfast spot")

        if not lunch:
            lunch = [{
                "name": f"Local Lunch Restaurant in {destination}",
                "lat": None,
                "lon": None,
                "rating": 4.0,
                "reviews": 100,
                "price_level": "₹₹",
                "address": f"Near {destination} City Center",
                "thumbnail": f"https://source.unsplash.com/featured/600x400/?lunch,restaurant,{destination}"
            }]
            print(f"⚠️ Created fallback lunch spot")

        if not dinner:
            dinner = [{
                "name": f"Popular Dinner Spot in {destination}",
                "lat": None,
                "lon": None,
                "rating": 4.0,
                "reviews": 100,
                "price_level": "₹₹₹",
                "address": f"Near {destination} City Center",
                "thumbnail": f"https://source.unsplash.com/featured/600x400/?dinner,restaurant,{destination}"
            }]
            print(f"⚠️ Created fallback dinner spot")

        if not hotels:
            hotels = [{
                "name": f"Recommended Hotel in {destination}",
                "lat": None,
                "lon": None,
                "rating": 4.0,
                "reviews": 100,
                "price_level": "₹₹₹",
                "address": f"Central {destination}",
                "thumbnail": f"https://source.unsplash.com/featured/600x400/?hotel,{destination}"
            }]
            print(f"⚠️ Created fallback hotel")


        # =================================================
        # 🔥 BUILD ITINERARY
        # =================================================

        itinerary = {

            "destination": destination,

            "traveler_name": traveler_name,

            "traveler_type": traveler_type,

            "budget": budget,

            "interests": interests,

            "days": [],

            "hotel_recommendations": hotels
        }

        used_places = set()
        activity_counter = 1

        # =================================================
        # 🔥 DAY LOOP (UPDATED WITH REALISTIC TRAVEL FLOW)
        # =================================================

        for d in range(days):

            current_time = datetime.strptime("08:00", "%H:%M")

            current_location = None
            day_region = None

            day_plan = {
                "day": d + 1,
                "activities": [],
                "route_points": []
            }

            # =====================================================
            # 🚩 STARTING POINT (ONLY ON DAY 1)
            # =====================================================

            if d == 0 and starting_place:

                start_lat = None
                start_lon = None
                start_name = starting_place

                if resolved_start and isinstance(resolved_start, dict):
                    start_name = resolved_start.get("name") or starting_place
                    start_lat = resolved_start.get("lat")
                    start_lon = resolved_start.get("lon")
                else:
                    start_name = starting_place
                    start_lat = None
                    start_lon = None

                start_activity = {
                    "time": "Start",
                    "name": start_name,
                    "lat": start_lat,
                    "lon": start_lon,
                    "type": "start_point",
                    "start_time": "08:00 AM",
                    "end_time": "08:15 AM",
                    "description": f"Start your journey from {starting_place}"
                }

                day_plan["activities"].append(start_activity)

                if start_lat and start_lon:
                    day_plan["route_points"].append({
                        "name": f"Start: {start_name}",
                        "lat": start_lat,
                        "lon": start_lon,
                        "type": "start",
                        "time": "Start"
                    })

                current_location = {"lat": start_lat, "lon": start_lon}
                current_time += timedelta(minutes=15)

            # =====================================================
            # 🍳 BREAKFAST
            # =====================================================

            if breakfast:

                b = self.pick_nearby_restaurant(breakfast, current_location)

                if b and isinstance(b, dict):

                    if current_location and b.get("lat") and b.get("lon"):
                        current_time, travel_block = self.add_travel_time(
                            day_plan,
                            current_time,
                            current_location,
                            b,
                            transport_mode
                        )

                    activity = self.format_place(b, "Breakfast")

                    duration = 60

                    activity["start_time"] = self.format_time(current_time)
                    current_time += timedelta(minutes=duration)
                    activity["end_time"] = self.format_time(current_time)

                    activity["activity_number"] = activity_counter
                    day_plan["activities"].append(activity)
                    activity_counter += 1

                    current_location = {
                        "lat": b.get("lat"),
                        "lon": b.get("lon")
                    }

            # =====================================================
            # 🌄 MORNING ACTIVITY
            # =====================================================

            morning_place = self.select_best_place(
                places=unique,
                current_time=current_time,
                used_places=used_places,
                must_visit_names=must_visit_names,
                destination=destination,
                preferred_types=["fort", "museum", "nature", "waterfall", "history"],
                current_location=current_location,
                ending_location=resolved_end,
                day_region=day_region,
            )

            if morning_place:

                # 🚗 TRAVEL
                current_time, travel_block = self.add_travel_time(
                    day_plan,
                    current_time,
                    current_location,
                    morning_place,
                    transport_mode
                )


                activity = self.format_place(morning_place, "Morning Activity")
                duration = self.estimate_visit_duration(morning_place)

                activity["start_time"] = self.format_time(current_time)
                current_time += timedelta(minutes=duration)
                activity["end_time"] = self.format_time(current_time)

                activity["activity_number"] = activity_counter
                day_plan["activities"].append(activity)
                activity_counter += 1

                used_places.add(morning_place.get("name"))
                day_region = morning_place.get("region")

                current_location = {
                    "lat": morning_place.get("lat"),
                    "lon": morning_place.get("lon")
                }

            # =====================================================
            # ☀️ AFTERNOON ACTIVITY
            # =====================================================

            afternoon_place = self.select_best_place(
                places=unique,
                current_time=current_time,
                used_places=used_places,
                must_visit_names=must_visit_names,
                destination=destination,
                preferred_types=interest_list,
                current_location=current_location,
                ending_location=resolved_end,
                day_region=day_region,
            )

            if afternoon_place:

                current_time, travel_block = self.add_travel_time(
                    day_plan,
                    current_time,
                    current_location,
                    afternoon_place,
                    transport_mode
                )


                activity = self.format_place(afternoon_place, "Afternoon Activity")
                duration = self.estimate_visit_duration(afternoon_place)

                activity["start_time"] = self.format_time(current_time)
                current_time += timedelta(minutes=duration)
                activity["end_time"] = self.format_time(current_time)

                activity["activity_number"] = activity_counter
                day_plan["activities"].append(activity)
                activity_counter += 1

                used_places.add(afternoon_place.get("name"))

                current_location = {
                    "lat": afternoon_place.get("lat"),
                    "lon": afternoon_place.get("lon")
                }

            # =====================================================
            # 🍽️ LUNCH
            # =====================================================

            if lunch and isinstance(lunch, list):

                l = self.pick_nearby_restaurant(lunch, current_location)

                if l and isinstance(l, dict):

                    current_time, travel_block = self.add_travel_time(
                        day_plan,
                        current_time,
                        current_location,
                        l,
                        transport_mode
                    )

                    activity = self.format_place(l, "Lunch")

                    duration = 75

                    activity["start_time"] = self.format_time(current_time)
                    current_time += timedelta(minutes=duration)
                    activity["end_time"] = self.format_time(current_time)

                    activity["activity_number"] = activity_counter
                    day_plan["activities"].append(activity)
                    activity_counter += 1

                    current_location = {
                        "lat": l.get("lat"),
                        "lon": l.get("lon")
                    }

            # =====================================================
            # 🌅 EVENING ACTIVITY
            # =====================================================

            evening_place = self.select_best_place(
                places=unique,
                current_time=current_time,
                used_places=used_places,
                must_visit_names=must_visit_names,
                destination=destination,
                preferred_types=interest_list,
                current_location=current_location,
                ending_location=resolved_end,
                day_region=day_region
            )

            if evening_place:

                current_time, travel_block = self.add_travel_time(
                    day_plan,
                    current_time,
                    current_location,
                    evening_place,
                    transport_mode
                )


                activity = self.format_place(evening_place, "Evening Activity")
                duration = self.estimate_visit_duration(evening_place)

                activity["start_time"] = self.format_time(current_time)
                current_time += timedelta(minutes=duration)
                activity["end_time"] = self.format_time(current_time)

                activity["activity_number"] = activity_counter
                day_plan["activities"].append(activity)
                activity_counter += 1

                used_places.add(evening_place.get("name"))

                current_location = {
                    "lat": evening_place.get("lat"),
                    "lon": evening_place.get("lon")
                }

            # =====================================================
            # 🌴 BEACH (OPTIONAL)
            # =====================================================

            if any(i in interests.lower() for i in ["beach", "beaches", "coast", "shore"]):

                beach_place = self.select_best_place(
                    places=unique,
                    current_time=current_time,
                    used_places=used_places,
                    must_visit_names=must_visit_names,
                    destination=destination,
                    preferred_types=["beach", "shore", "coast", "sunset"],
                    current_location=current_location,
                    ending_location=resolved_end,
                    day_region=day_region
                )

                if beach_place:

                    current_time, travel_block = self.add_travel_time(
                        day_plan,
                        current_time,
                        current_location,
                        beach_place,
                        transport_mode
                    )

                    activity = self.format_place(beach_place, "Beach Sunset")
                    duration = 120

                    activity["start_time"] = self.format_time(current_time)
                    current_time += timedelta(minutes=duration)
                    activity["end_time"] = self.format_time(current_time)

                    activity["activity_number"] = activity_counter
                    day_plan["activities"].append(activity)
                    activity_counter += 1

                    used_places.add(beach_place.get("name"))

                    current_location = {
                        "lat": beach_place.get("lat"),
                        "lon": beach_place.get("lon")
                    }

            # =====================================================
            # 🍷 DINNER
            # =====================================================

            if dinner and isinstance(dinner, list):

                dn = self.pick_nearby_restaurant(dinner, current_location)

                if dn and isinstance(dn, dict):

                    current_time, travel_block = self.add_travel_time(
                        day_plan,
                        current_time,
                        current_location,
                        dn,
                        transport_mode
                    )

                    activity = self.format_place(dn, "Dinner")

                    duration = 90

                    activity["start_time"] = self.format_time(current_time)
                    current_time += timedelta(minutes=duration)
                    activity["end_time"] = self.format_time(current_time)

                    activity["activity_number"] = activity_counter
                    day_plan["activities"].append(activity)
                    activity_counter += 1

                    current_location = {
                        "lat": dn.get("lat"),
                        "lon": dn.get("lon")
                    }

            # =====================================================
            # 🌙 NIGHTLIFE
            # =====================================================

            if include_nightlife:

                nightlife = self.select_best_place(
                    places=nightlife_places,
                    current_time=current_time,
                    used_places=used_places,
                    must_visit_names=must_visit_names,
                    destination=destination,
                    preferred_types=["nightlife", "club", "pub", "bar"],
                    current_location=current_location,
                    ending_location=resolved_end,
                    day_region=day_region
                )

                if nightlife:

                    current_time, travel_block = self.add_travel_time(
                        day_plan,
                        current_time,
                        current_location,
                        nightlife,
                        transport_mode
                    )


                    activity = self.format_place(nightlife, "Nightlife")
                    duration = 120

                    activity["start_time"] = self.format_time(current_time)
                    current_time += timedelta(minutes=duration)
                    activity["end_time"] = self.format_time(current_time)

                    activity["activity_number"] = activity_counter
                    day_plan["activities"].append(activity)
                    activity_counter += 1

                    used_places.add(nightlife.get("name"))

                    current_location = {
                        "lat": nightlife.get("lat"),
                        "lon": nightlife.get("lon")
                    }

            # =====================================================
            # 🏨 HOTEL
            # =====================================================

            if hotels and isinstance(hotels, list):

                center_location = self.get_route_center(day_plan["route_points"])

                blended_location = (
                    current_location or center_location
                )

                hotel = self.pick_nearby_hotel(hotels, blended_location)

                if hotel and isinstance(hotel, dict):

                    current_time, travel_block = self.add_travel_time(
                        day_plan,
                        current_time,
                        current_location,
                        hotel,
                        transport_mode
                    )

                    day_plan["stay"] = self.format_place(
                        hotel,
                        "Stay",
                        is_hotel=True
                    )

                    if (
                        day_plan["stay"].get("lat")
                        and day_plan["stay"].get("lon")
                    ):
                        day_plan["route_points"].append({
                            "name": day_plan["stay"].get("name"),
                            "lat": day_plan["stay"].get("lat"),
                            "lon": day_plan["stay"].get("lon"),
                            "type": "hotel",
                            "time": "Stay"
                        })

            # =====================================================
            # 🏁 ENDING POINT
            # =====================================================

            if d == days - 1 and ending_place:

                end_lat = None
                end_lon = None
                end_name = ending_place

                if resolved_end and isinstance(resolved_end, dict):
                    end_name = resolved_end.get("name") or ending_place
                    end_lat = resolved_end.get("lat")
                    end_lon = resolved_end.get("lon")
                else:
                    end_name = ending_place
                    end_lat = None
                    end_lon = None

                day_plan["activities"].append({
                    "time": "End",
                    "name": end_name,
                    "lat": end_lat,
                    "lon": end_lon,
                    "type": "end_point",
                    "start_time": self.format_time(current_time),
                    "end_time": self.format_time(current_time + timedelta(minutes=15)),
                    "description": f"End your journey at {ending_place}"
                })

                if end_lat and end_lon:
                    day_plan["route_points"].append({
                        "name": f"End: {end_name}",
                        "lat": end_lat,
                        "lon": end_lon,
                        "type": "end",
                        "time": "End"
                    })

            # =====================================================
            # 📊 ESTIMATION
            # =====================================================

            total_places = len(day_plan["activities"])

            day_plan["estimated_distance_km"] = round(total_places * 8.5, 1)
            day_plan["estimated_travel_time"] = f"{total_places * 20} mins"

            if budget == "budget":
                day_budget = 3500
            elif budget == "luxury":
                day_budget = 18000
            else:
                day_budget = 7500

            day_plan["estimated_budget"] = day_budget

            itinerary["days"].append(day_plan)

        # =================================================
        # 🔥 AI INSIGHTS
        # =================================================

        try:

            insights = (
                self.groq.optimize_itinerary(
                    destination,
                    days,
                    interests,
                    unique,
                    (
                        self.safe_list(breakfast)
                        + self.safe_list(lunch)
                        + self.safe_list(dinner)
                    ),
                    self.safe_list(hotels)
                )
            )

            itinerary["ai_insights"] = insights

        except Exception as e:

            print(
                "⚠️ AI insight error:",
                e
            )
        return itinerary

    # =====================================================
    # 🔥 REVIEWS
    # =====================================================

    def get_place_reviews(

        self,

        place_name,

        destination,

        lat=None,

        lon=None
    ):

        return self.serpapi.get_place_reviews(

            place_name=place_name,

            destination=destination,

            lat=lat,

            lon=lon
        )


# =========================================================
# 🔥 INSTANCE
# =========================================================

generator = AIItineraryGenerator()