# ai_engine/services.py - COMPLETE WORKING VERSION
from math import radians, sin, cos, sqrt, atan2
from datetime import time
from destinations.models import Attraction
from restaurants.models import RestaurantProfile

def get_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points in KM"""
    if not all([lat1, lon1, lat2, lon2]):
        return 0
    
    R = 6371
    lat1_rad = radians(lat1)
    lat2_rad = radians(lat2)
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    
    a = sin(dlat/2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    return R * c

def estimate_travel_time(distance_km, mode="car"):
    """Estimate travel time in minutes"""
    speeds = {
        "car": 35,
        "bike": 30,
        "bus": 25,
        "walk": 5,
        "train": 50
    }
    speed = speeds.get(mode, 30)
    
    if distance_km == 0:
        return 0
    
    travel_minutes = (distance_km / speed) * 60
    return int(travel_minutes + 10)  # Add 10 min buffer

def find_nearby_hotels(lat, lon, radius_km=2):
    """Find nearby hotels"""
    radius_deg = radius_km / 111
    try:
        hotels = RestaurantProfile.objects.filter(
            latitude__range=(lat - radius_deg, lat + radius_deg),
            longitude__range=(lon - radius_deg, lon + radius_deg),
            category__in=["hotel", "resort", "stay"]
        ).order_by("-rating")[:3]
        return list(hotels)
    except:
        return []

def find_nearby_restaurants(lat, lon, radius_km=1):
    """Find nearby restaurants"""
    radius_deg = radius_km / 111
    try:
        restaurants = RestaurantProfile.objects.filter(
            latitude__range=(lat - radius_deg, lat + radius_deg),
            longitude__range=(lon - radius_deg, lon + radius_deg),
            category__in=["restaurant", "cafe", "dining"]
        ).order_by("-rating")[:3]
        return list(restaurants)
    except:
        return []

def generate_smart_itinerary(destination, plan):
    """Generate itinerary based on attractions"""
    
    print(f"\n{'='*60}")
    print(f"🎯 GENERATING ITINERARY FOR: {destination.name}")
    print(f"{'='*60}")
    
    # Get all attractions
    attractions = list(destination.attractions.all())
    print(f"📊 Total attractions found: {len(attractions)}")
    
    if not attractions:
        print("❌ No attractions found!")
        return {"days": [], "budget": 0, "destination_score": 0}
    
    # Sort attractions by priority (higher priority first)
    attractions.sort(key=lambda x: x.priority_score, reverse=True)
    
    # Calculate how many attractions per day
    total_attractions = len(attractions)
    days_needed = plan.number_of_days
    attractions_per_day = max(2, total_attractions // days_needed)
    
    print(f"📅 Planning for {days_needed} days, {attractions_per_day} attractions per day")
    
    # Split attractions into days
    daily_attractions = []
    for i in range(days_needed):
        start_idx = i * attractions_per_day
        end_idx = start_idx + attractions_per_day
        day_places = attractions[start_idx:end_idx]
        if day_places:
            daily_attractions.append(day_places)
        else:
            daily_attractions.append([])
    
    # Schedule each day
    scheduled_days = []
    
    for day_num, day_places in enumerate(daily_attractions, 1):
        print(f"\n📅 Scheduling Day {day_num} with {len(day_places)} attractions")
        
        if not day_places:
            scheduled_days.append({
                "morning": [],
                "afternoon": [],
                "evening": [],
                "night": [],
                "stay": None,
                "total_activities": 0,
                "total_travel_time": 0
            })
            continue
        
        # Get start time (9 AM default)
        start_time_minutes = 540  # 9:00 AM
        current_time = start_time_minutes
        
        # Start from destination center or specified start location
        if plan.start_latitude and plan.start_longitude:
            current_location = (plan.start_latitude, plan.start_longitude)
        else:
            current_location = (destination.latitude, destination.longitude)
        
        timeline = []
        
        # Sort day places by best time of day
        morning_places = [p for p in day_places if p.best_time_of_day == "morning"]
        afternoon_places = [p for p in day_places if p.best_time_of_day == "afternoon"]
        evening_places = [p for p in day_places if p.best_time_of_day == "evening"]
        night_places = [p for p in day_places if p.best_time_of_day == "night"]
        any_places = [p for p in day_places if p.best_time_of_day == "any"]
        
        # Reorder: morning -> afternoon -> evening -> night, with any filling gaps
        ordered_places = morning_places + any_places[:2] + afternoon_places + any_places[2:4] + evening_places + night_places
        
        for attraction in ordered_places:
            # Calculate travel time from current location
            dist = get_distance(
                current_location[0], current_location[1],
                attraction.latitude, attraction.longitude
            )
            travel_time = estimate_travel_time(dist, plan.transport_mode)
            
            # Calculate arrival time
            arrival_time = current_time + travel_time
            arrival_hour = int(arrival_time // 60)
            arrival_min = int(arrival_time % 60)
            
            # Check if arrival time is reasonable (before 9 PM)
            if arrival_hour >= 21:
                print(f"  ⏰ Skipping {attraction.name} - would arrive too late ({arrival_hour}:{arrival_min:02d})")
                continue
            
            # Calculate visit duration
            visit_duration = attraction.average_time_needed or 60
            
            # Adjust based on pace
            if hasattr(plan, 'pace'):
                if plan.pace == "fast":
                    visit_duration = int(visit_duration * 0.7)
                elif plan.pace == "slow":
                    visit_duration = int(visit_duration * 1.3)
            
            # Calculate departure time
            departure_time = arrival_time + visit_duration
            departure_hour = int(departure_time // 60)
            departure_min = int(departure_time % 60)
            
            # Find nearby restaurants and hotels
            nearby_restaurants = find_nearby_restaurants(attraction.latitude, attraction.longitude)
            nearby_hotels = find_nearby_hotels(attraction.latitude, attraction.longitude)
            
            # Add to timeline
            timeline.append({
                "place": attraction,
                "arrival_time": f"{arrival_hour:02d}:{arrival_min:02d}",
                "departure_time": f"{departure_hour:02d}:{departure_min:02d}",
                "visit_duration": visit_duration,
                "distance_from_prev": round(dist, 2),
                "travel_time": travel_time,
                "nearby_restaurants": nearby_restaurants[:2],
                "nearby_hotels": nearby_hotels[:1],
                "is_open": True
            })
            
            # Update for next attraction
            current_time = departure_time + 30  # 30 min break
            current_location = (attraction.latitude, attraction.longitude)
            
            print(f"  ✓ Added: {attraction.name} at {arrival_hour:02d}:{arrival_min:02d}")
        
        # Find hotel for the night
        stay = None
        if timeline:
            last_place = timeline[-1]["place"]
            hotels = find_nearby_hotels(last_place.latitude, last_place.longitude)
            stay = hotels[0] if hotels else None
        
        # Split timeline into time slots
        morning = [t for t in timeline if int(t["arrival_time"].split(":")[0]) < 12]
        afternoon = [t for t in timeline if 12 <= int(t["arrival_time"].split(":")[0]) < 17]
        evening = [t for t in timeline if 17 <= int(t["arrival_time"].split(":")[0]) < 20]
        night = [t for t in timeline if int(t["arrival_time"].split(":")[0]) >= 20]
        
        scheduled_days.append({
            "morning": morning,
            "afternoon": afternoon,
            "evening": evening,
            "night": night,
            "stay": stay,
            "total_activities": len(timeline),
            "total_travel_time": sum(t["travel_time"] for t in timeline)
        })
    
    # Calculate total budget
    total_budget = 0
    for day in scheduled_days:
        total_budget += plan.number_of_days * 1500  # Base cost per day
        total_budget += sum(a.get("place", {}).entry_fee or 0 for a in day.get("morning", []))
        total_budget += sum(a.get("place", {}).entry_fee or 0 for a in day.get("afternoon", []))
        total_budget += sum(a.get("place", {}).entry_fee or 0 for a in day.get("evening", []))
    
    # Calculate score
    total_attractions_used = sum(len(day.get("morning", [])) + len(day.get("afternoon", [])) + 
                                  len(day.get("evening", [])) + len(day.get("night", [])) 
                                  for day in scheduled_days)
    destination_score = (total_attractions_used / max(len(attractions), 1)) * 100
    
    print(f"\n{'='*60}")
    print(f"✅ GENERATION COMPLETE!")
    print(f"📊 Total days: {len(scheduled_days)}")
    print(f"🎯 Total activities: {total_attractions_used}")
    print(f"💰 Budget: ₹{total_budget}")
    print(f"⭐ Score: {destination_score:.1f}%")
    print(f"{'='*60}\n")
    
    return {
        "days": scheduled_days,
        "budget": total_budget,
        "destination_score": destination_score,
        "total_attractions": total_attractions_used,
        "total_days": len(scheduled_days)
    }
