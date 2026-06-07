from django.urls import path
from . import views

app_name = "destinations"

urlpatterns = [

    # =====================================================
    # DESTINATION LIST (Explore page)
    # =====================================================
    path(
        "",
        views.destination_list,
        name="destination_list"
    ),

    # =====================================================
    # DESTINATION DETAIL
    # =====================================================
    path(
        "destination/<int:destination_id>/",
        views.destination_detail,
        name="destination_detail"
    ),

    # =====================================================
    # PLACE DETAIL
    # =====================================================
    path(
    "destination/<int:destination_id>/place/<int:place_id>/",
    views.place_detail,
    name="place_detail"
),

    # =====================================================
    # ADD DESTINATION
    # =====================================================
    path(
        "add/",
        views.add_destination,
        name="add_destination"
    ),

    path('api/get-coordinates/', views.get_coordinates_api, name='get_coordinates_api'),

    # =====================================================
    # ADD PLACE (inside destination)
    # =====================================================
    path(
        "destination/<int:destination_id>/add-place/",
        views.add_place,
        name="add_place"
    ),

    # =====================================================
    # ADD REVIEW
    # =====================================================
    path(
        "place/<int:place_id>/add-review/",
        views.add_review,
        name="add_review"
    ),

    path(
        "destination/edit/<int:destination_id>/",
        views.edit_destination,
        name="edit_destination"
),

    path(
        "place/edit/<int:place_id>/",
        views.edit_place,
        name="edit_place"
),
    path(
    "destination/delete/<int:destination_id>/",
    views.delete_destination,
    name="delete_destination"
),

    path('review/<int:review_id>/edit/', views.edit_review, name='edit_review'),
    path('review/<int:review_id>/delete/', views.delete_review, name='delete_review'),

    path(
        "place/<int:place_id>/delete/",
        views.delete_place,
        name="delete_place"
    ),

    path(
    "destination/<int:destination_id>/add-review/",
    views.add_destination_review,
    name="add_destination_review"
),

path(
    "destination-review/<int:review_id>/edit/",
    views.edit_destination_review,
    name="edit_destination_review"
),

path(
    "destination-review/<int:review_id>/delete/",
    views.delete_destination_review,
    name="delete_destination_review"
),

path(
    "approve-destination/<int:destination_id>/",
    views.approve_destination,
    name="approve_destination"
),

path(
    "reject-destination/<int:destination_id>/",
    views.reject_destination,
    name="reject_destination"
),

path(
    "approve-place/<int:place_id>/",
    views.approve_place,
    name="approve_place"
),

path(
    "reject-place/<int:place_id>/",
    views.reject_place,
    name="reject_place"
),

]