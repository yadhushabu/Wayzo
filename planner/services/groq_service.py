# planner/services/groq_service.py
from groq import Groq
from django.conf import settings

class GroqItineraryOptimizer:
    """Use Groq's Llama to provide intelligent itinerary optimization"""
    
    def __init__(self):
        self.client = Groq(api_key=settings.GROQ_API_KEY)
    
    def optimize_itinerary(self, destination, days, interests, attractions, restaurants, hotels):
        """Get AI-powered suggestions to optimize the itinerary"""
        
        prompt = f"""
        You are an expert travel planner AI. Analyze this itinerary for {destination} and provide:
        
        1. LOGICAL FLOW CHECK: Are the attractions ordered efficiently by location?
        2. TIME OPTIMIZATION: Suggest any timing adjustments
        3. HIDDEN GEMS: Recommend 2-3 lesser-known spots related to {interests}
        4. LOCAL INSIGHTS: Share 2 unique tips about {destination}
        5. Why this itinerary matches {interests} interests
        
        Attractions found: {[a.get('name') for a in attractions[:10]]}
        Restaurants found: {[r.get('name') for r in restaurants[:5]]}
        
        Keep response concise and actionable.
        """
        
        try:
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",  # ← Added missing comma
                messages=[
                    {"role": "system", "content": "You are an expert travel planner AI. Provide concise, actionable advice."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            return response.choices[0].message.content
        except Exception as e:
            print(f"Groq API error: {e}")
            return None
    
    def generate_place_description(self, place_name, place_type, destination, interests):
        """Generate intelligent, engaging description for a place"""
        
        prompt = f"""
        Write a short, engaging description (under 50 words) for {place_name} in {destination}.
        Type: {place_type}
        User interests: {interests}
        
        Make it exciting but factual. Include why someone with {interests} interests would love it.
        """
        
        try:
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",  # ← Added missing comma
                messages=[
                    {"role": "system", "content": "You write engaging, concise travel descriptions."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                max_tokens=120
            )
            
            return response.choices[0].message.content
        except Exception as e:
            print(f"Groq description error: {e}")
            return None
    
    def get_daily_summary(self, day_activities, destination, interests):
        """Generate a poetic/engaging summary for each day"""
        
        if not day_activities:
            return f"A wonderful day exploring {destination}!"
            
        activities_summary = ', '.join([a.get('name', '') for a in day_activities[:4]])
        
        prompt = f"""
        Write ONE engaging sentence summarizing Day {day_activities[0].get('day', 1)} in {destination}.
        Activities include: {activities_summary}
        User loves: {interests}
        
        Make it inspiring, like a travel journal entry.
        """
        
        try:
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",  # ← Added missing comma
                messages=[
                    {"role": "system", "content": "You write inspiring, poetic travel summaries in one sentence."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.9,
                max_tokens=100
            )
            
            return response.choices[0].message.content
        except Exception as e:
            print(f"Groq summary error: {e}")
            return None


# Create instance
groq_optimizer = GroqItineraryOptimizer()