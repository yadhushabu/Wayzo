# services/llm_planner.py
import requests
import json

class LLMItineraryPlanner:
    """Use LLM to understand user preferences and generate plans"""
    
    def __init__(self):
        # Use OpenRouter (access to multiple LLMs with free tier)
        self.serpapi_url = "https://openrouter.ai/api/v1/chat/completions"
        self.serpapi_key = "your_free_openrouter_key"  # Free tier available
        
    def understand_preferences(self, destination, days, interests):
        """Use LLM to deeply understand user intentions"""
        
        prompt = f"""
        You are a travel planning AI. A user wants to visit {destination} for {days} days.
        Their interests: {interests}.
        
        Analyze their preferences and output structured data:
        1. Infer what type of traveler they are (solo/couple/family/friends)
        2. What pace suits them (relaxed/moderate/packed)
        3. What specific activities would match their interests
        4. What time of day they'd prefer for different activities
        
        Return as JSON.
        """
        
        response = requests.post(
            self.serpapi_url,
            headers={"Authorization": f"Bearer {self.serpapi_key}"},
            json={
                "model": "gpt-3.5-turbo",  # Or free models like "mistral-7b"
                "messages": [{"role": "user", "content": prompt}]
            }
        )
        return response.json()