from django.urls import path
from . import views

urlpatterns = [
    path("create/", views.create_destination, name="create_destination"),
    path("", views.destination_list, name="destination_list"),
    path("<slug:slug>/", views.destination_detail, name="destination_detail"),
    path("<slug:slug>/add-attraction/", views.add_attraction, name="add_attraction"),
    path("attraction/delete/<int:id>/", views.delete_attraction, name="delete_attraction"),
    path('api/destinations/', views.api_destinations, name='api_destinations'),
    path('api/destination-coords/<int:dest_id>/', views.destination_coords, name='destination_coords'),
    path("attraction/<int:id>/", views.attraction_detail, name="attraction_detail"),
    path("attraction/<int:id>/edit/", views.edit_attraction, name="edit_attraction"),
]