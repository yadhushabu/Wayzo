# ai_engine/auto.py
from math import radians, sin, cos, sqrt, atan2
import requests
from destinations.models import Attraction

def get_distance(lat1, lon1, lat2, lon2):
    R = 6371  # KM
    
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    return R * c

def generate_attractions_from_api(destination, api_key=None):
    """Generate attractions using OpenTripMap API"""
    if not api_key:
        # Use a demo key or get from settings
        api_key = "YOUR_OPENTRIPMAP_API_KEY"  # Get free key from https://opentripmap.io/product
    
    url = f"https://api.opentripmap.com/0.1/en/places/radius"
    params = {
        "radius": 10000,  # 10km radius
        "lat": destination.latitude,
        "lon": destination.longitude,
        "rate": 2,
        "format": "json",
        "apikey": api_key,
        "limit": 30
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        return data.get('features', [])
    except Exception as e:
        print(f"API Error: {e}")
        return []

def create_attraction_from_data(destination, item):
    """Create attraction from API data"""
    props = item.get('properties', {})
    coords = item.get('geometry', {}).get('coordinates', [])
    
    name = props.get('name')
    if not name or name.strip() == "":
        return None
    
    # Skip duplicates
    if Attraction.objects.filter(destination=destination, name__iexact=name).exists():
        return None
    
    kinds = props.get('kinds', '').lower()
    
    # Determine experience type
    experience_map = {
        'beach': 'relaxed',
        'waterfall': 'adventure',
        'nature': 'adventure',
        'temple': 'spiritual',
        'church': 'spiritual',
        'museum': 'cultural',
        'nightclub': 'nightlife',
        'bar': 'nightlife',
        'park': 'relaxed',
        'garden': 'relaxed'
    }
    
    experience = 'relaxed'
    for key, value in experience_map.items():
        if key in kinds:
            experience = value
            break
    
    # Determine best time
    if 'nightclub' in kinds or 'bar' in kinds:
        best_time = 'night'
    elif 'beach' in kinds:
        best_time = 'evening'
    elif 'temple' in kinds or 'church' in kinds:
        best_time = 'morning'
    elif 'museum' in kinds:
        best_time = 'afternoon'
    else:
        best_time = 'any'
    
    # Estimate time needed
    if 'waterfall' in kinds or 'trekking' in kinds:
        avg_time = 120
    elif 'museum' in kinds or 'zoo' in kinds:
        avg_time = 90
    elif 'beach' in kinds or 'park' in kinds:
        avg_time = 120
    elif 'nightclub' in kinds:
        avg_time = 180
    else:
        avg_time = 60
    
    # Determine suitable for
    suitable = "family,friends"
    if 'romantic' in kinds:
        suitable = "couples"
    elif 'adventure' in kinds:
        suitable = "friends,family"
    
    return Attraction(
        destination=destination,
        name=name,
        description=props.get('description', props.get('kinds', 'Beautiful place to visit')),
        latitude=coords[1] if coords else destination.latitude,
        longitude=coords[0] if coords else destination.longitude,
        priority_score=3,
        best_time_of_day=best_time,
        average_time_needed=avg_time,
        experience_type=experience,
        suitable_for=suitable,
        tags=kinds
    )

def generate_attractions(destination):
    """Main function to generate attractions for a destination"""
    print(f"\n🔍 Generating attractions for {destination.name}...")
    
    # First, try API
    api_data = generate_attractions_from_api(destination)
    
    created = 0
    
    if api_data:
        print(f"✅ Found {len(api_data)} attractions from API")
        for item in api_data:
            attraction = create_attraction_from_data(destination, item)
            if attraction:
                attraction.save()
                created += 1
        print(f"📝 Created {created} attractions from API")
    
    # If no attractions from API or need more, add fallback attractions
    if created < 5:
        print("⚠️ Adding fallback attractions...")
        add_fallback_attractions(destination)
        created += 5
    
    print(f"✨ Total {created} attractions added for {destination.name}")
    return created

def add_fallback_attractions(destination):
    """Add fallback attractions if API fails"""
    fallback_attractions = {
        "Goa": [
            {"name": "Baga Beach", "lat": 15.5594, "lon": 73.7395, "type": "beach", "time": 120},
            {"name": "Calangute Beach", "lat": 15.5434, "lon": 73.7556, "type": "beach", "time": 120},
            {"name": "Fort Aguada", "lat": 15.4935, "lon": 73.7684, "type": "heritage", "time": 60},
            {"name": "Basilica of Bom Jesus", "lat": 15.5000, "lon": 73.9117, "type": "spiritual", "time": 45},
            {"name": "Dudhsagar Falls", "lat": 15.3122, "lon": 74.3144, "type": "adventure", "time": 180},
            {"name": "Anjuna Beach", "lat": 15.5800, "lon": 73.7400, "type": "beach", "time": 120},
            {"name": "Chapora Fort", "lat": 15.6030, "lon": 73.7392, "type": "heritage", "time": 60},
            {"name": "Palolem Beach", "lat": 15.0100, "lon": 74.0240, "type": "beach", "time": 120},
        ],
        "Manali": [
            {"name": "Solang Valley", "lat": 32.3165, "lon": 77.1655, "type": "adventure", "time": 180},
            {"name": "Hadimba Temple", "lat": 32.2396, "lon": 77.1888, "type": "spiritual", "time": 45},
            {"name": "Rohtang Pass", "lat": 32.3667, "lon": 77.2500, "type": "adventure", "time": 240},
        ]
    }
    
    # Default for any destination
    default_attractions = [
        {"name": "City Center", "lat": destination.latitude, "lon": destination.longitude, "type": "relaxed", "time": 60},
        {"name": "Local Market", "lat": destination.latitude + 0.01, "lon": destination.longitude + 0.01, "type": "shopping", "time": 90},
        {"name": "Scenic Viewpoint", "lat": destination.latitude - 0.01, "lon": destination.longitude - 0.01, "type": "relaxed", "time": 45},
    ]
    
    # Get attractions for specific destination or use default
    attractions_list = fallback_attractions.get(destination.name, default_attractions)
    
    for attr_data in attractions_list:
        if not Attraction.objects.filter(destination=destination, name=attr_data["name"]).exists():
            # Map type to experience
            exp_map = {
                "beach": "relaxed",
                "heritage": "cultural",
                "spiritual": "spiritual",
                "adventure": "adventure",
                "shopping": "relaxed",
                "relaxed": "relaxed"
            }
            
            Attraction.objects.create(
                destination=destination,
                name=attr_data["name"],
                description=f"Popular {attr_data['type']} attraction in {destination.name}",
                latitude=attr_data["lat"],
                longitude=attr_data["lon"],
                priority_score=3,
                best_time_of_day="morning" if "Temple" in attr_data["name"] else "afternoon",
                average_time_needed=attr_data["time"],
                experience_type=exp_map.get(attr_data["type"], "relaxed"),
                suitable_for="family,friends,couples",
                tags=attr_data["type"]
            )