from datetime import datetime
from .weather_service import WeatherService


class RankingEngine:

    # -----------------------------
    # WEIGHTS (tunable AI system)
    # -----------------------------
    WEIGHTS = {
        "trending": 0.30,
        "season": 0.20,
        "weather": 0.25,
        "content": 0.15,
        "rating": 0.10,
    }

    # -----------------------------
    # CITY TRENDING BASE SCORE
    # -----------------------------
    TRENDING_BASE = {
        "Goa": 90,
        "Kerala": 85,
        "Manali": 80,
        "Kashmir": 88,
        "default": 60
    }

    # -----------------------------
    # SEASON DATA
    # -----------------------------
    SEASON_DATA = {
        "Goa": [11, 12, 1, 2, 3],
        "Kerala": [10, 11, 12, 1],
        "Manali": [3, 4, 5, 12, 1],
        "Kashmir": [4, 5, 6, 10, 11],
    }

    # =====================================================
    # MAIN CALCULATOR (DESTINATION / PLACE)
    # =====================================================

    def calculate(self, city, attractions_count=0, rating=0):

        weather = WeatherService.get_weather(city)

        month = datetime.now().month

        # -------------------------
        # 1. TRENDING SCORE
        # -------------------------
        trending_score = self.TRENDING_BASE.get(city, self.TRENDING_BASE["default"])

        # -------------------------
        # 2. SEASON SCORE
        # -------------------------
        season_score = 0
        if month in self.SEASON_DATA.get(city, []):
            season_score = 100
        else:
            season_score = 40

        # -------------------------
        # 3. WEATHER SCORE
        # -------------------------
        weather_score = 50

        if weather:
            temp = weather["temp"]
            humidity = weather["humidity"]

            # ideal travel weather
            if 20 <= temp <= 30:
                weather_score += 40
            elif 15 <= temp < 20 or 30 < temp <= 35:
                weather_score += 20
            else:
                weather_score += 5

            # humidity penalty
            if humidity > 85:
                weather_score -= 15

        # -------------------------
        # 4. CONTENT SCORE
        # -------------------------
        content_score = min(attractions_count * 2, 100)

        # -------------------------
        # 5. RATING SCORE
        # -------------------------
        rating_score = rating * 20  # assuming rating is 0–5

        # -------------------------
        # FINAL SCORE (weighted)
        # -------------------------
        final_score = (
            trending_score * self.WEIGHTS["trending"] +
            season_score * self.WEIGHTS["season"] +
            weather_score * self.WEIGHTS["weather"] +
            content_score * self.WEIGHTS["content"] +
            rating_score * self.WEIGHTS["rating"]
        )

        return round(final_score, 2)

    # =====================================================
    # BREAKDOWN (FOR UI DISPLAY)
    # =====================================================

    def breakdown(self, city, attractions_count=0, rating=0):

        weather = WeatherService.get_weather(city)
        month = datetime.now().month

        trending_score = self.TRENDING_BASE.get(city, 60)

        season_score = 100 if month in self.SEASON_DATA.get(city, []) else 40

        weather_score = 50
        if weather:
            temp = weather["temp"]
            humidity = weather["humidity"]

            if 20 <= temp <= 30:
                weather_score += 40
            elif 15 <= temp < 20 or 30 < temp <= 35:
                weather_score += 20
            else:
                weather_score += 5

            if humidity > 85:
                weather_score -= 15

        content_score = min(attractions_count * 2, 100)
        rating_score = rating * 20

        return {
            "trending_score": trending_score,
            "season_score": season_score,
            "weather_score": round(weather_score, 2),
            "content_score": content_score,
            "rating_score": rating_score,
        }