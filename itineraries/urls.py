from django.urls import path
from . import views

urlpatterns = [
    path('generate/<int:destination_id>/', views.generate_itinerary, name='generate_itinerary'),
    path('<int:itinerary_id>/customize/', views.customize_itinerary, name='customize_itinerary'),
    path('<int:itinerary_id>/regenerate-day/<int:day_number>/', views.regenerate_day, name='regenerate_day'),
    path('<int:itinerary_id>/save-note/', views.save_itinerary_note, name='save_itinerary_note'),
]