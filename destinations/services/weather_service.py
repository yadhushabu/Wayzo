import requests
from django.conf import settings


class WeatherService:
    BASE_URL = "https://api.openweathermap.org/data/2.5/weather"

    @classmethod
    def get_weather(cls, city):

        if not city:
            return None

        params = {
            "q": city,
            "appid": settings.OPENWEATHER_API_KEY,
            "units": "metric"
        }

        try:
            response = requests.get(
                cls.BASE_URL,
                params=params,
                timeout=8
            )

            if response.status_code != 200:
                return None

            data = response.json()

            return {
                "temp": float(data["main"]["temp"]),
                "description": data["weather"][0]["description"],
                "humidity": float(data["main"]["humidity"]),
                "icon": data["weather"][0]["icon"],
                "wind": float(data["wind"]["speed"])
            }

        except Exception as e:
            print("❌ Weather Error:", e)
            return None