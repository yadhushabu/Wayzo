class UserProfile:

    def __init__(self, user_id):

        self.user_id = user_id

        self.preferred_foods = []
        self.liked_places = []
        self.disliked_places = []

        self.favorite_activity_types = []

        self.walking_preference = "moderate"  # low / moderate / high

        self.budget_style = "mid"  # budget / mid / luxury

    # =====================================================
    # 🔥 UPDATE PREFERENCES
    # =====================================================

    def update_preferences(
        self,
        preferred_foods=None,
        liked_places=None,
        disliked_places=None,
        favorite_activity_types=None,
        walking_preference=None,
        budget_style=None
    ):

        if preferred_foods is not None:
            self.preferred_foods = preferred_foods

        if liked_places is not None:
            self.liked_places = liked_places

        if disliked_places is not None:
            self.disliked_places = disliked_places

        if favorite_activity_types is not None:
            self.favorite_activity_types = favorite_activity_types

        if walking_preference is not None:
            self.walking_preference = walking_preference

        if budget_style is not None:
            self.budget_style = budget_style

    # =====================================================
    # 🔥 EXPORT AS DICTIONARY
    # =====================================================

    def to_dict(self):

        return {
            "preferred_foods": set(self.preferred_foods),
            "liked_places": set(self.liked_places),
            "disliked_places": set(self.disliked_places),
            "favorite_activity_types": set(self.favorite_activity_types),
            "walking_preference": self.walking_preference,
            "budget_style": self.budget_style
        }