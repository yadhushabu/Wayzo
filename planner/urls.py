# planner/urls.py

from django.urls import path

from . import views_dynamic
from . import views


urlpatterns = [

    # =====================================================
    # 🔥 PAGE 1 → PLANNER INPUT PAGE
    # =====================================================

    path(
        '',
        views.planner,
        name='planner'
    ),

    # =====================================================
    # 🔥 PAGE 2 → GENERATED ITINERARY PAGE
    # =====================================================

    path(
        'itinerary/',
        views.generate_itinerary,
        name='generate_itinerary'
    ),

    # =====================================================
    # 🔥 AJAX REVIEWS API
    # =====================================================

    path(
        'get-reviews/',
        views.get_reviews,
        name='get_reviews'
    ),

    path(
    "api/alternatives/",
    views_dynamic.get_alternatives,
    name="alternatives"
),

    path(
    'api/save-itinerary/',
    views.save_itinerary,
    name='save_itinerary'
),
    path('planner/replace-hotel/', views.replace_hotel, name='replace_hotel'),

    path(
    "replace-activity/",
    views_dynamic.replace_activity,
    name="replace_activity"
)


]