# restaurants/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path("dashboard/", views.restaurant_dashboard, name="restaurant_dashboard"),
    
    # Property Management
    path("manage-property/", views.manage_property, name="manage_property"),
    path("manage-table-layout/", views.manage_table_layout, name="manage_table_layout"),
    
    # Delete operations
    path("delete-table/<int:id>/", views.delete_table, name="delete_table"),
    path("delete-room-type/<int:id>/", views.delete_room_type, name="delete_room_type"),
    path("delete-media/<int:id>/", views.delete_media, name="delete_media"),
    
    # Room management (individual rooms)
    path("add-room/<int:room_type_id>/", views.add_room, name="add_room"),
    path("edit-room/<int:room_id>/", views.edit_room, name="edit_room"),
    path("delete-room/<int:room_id>/", views.delete_room, name="delete_room"),
    
    # Room type edit (AJAX)
    path("api/room-type/<int:room_type_id>/", views.api_room_type_detail, name="api_room_type_detail"),
    path("edit-room-type/<int:room_type_id>/", views.edit_room_type, name="edit_room_type"),
    
    # Table API
    path("api/table/<int:table_id>/", views.api_table_crud, name="api_table_detail"),
    path("api/table/add/", views.api_table_crud, name="api_table_add"),
    path("api/table/<int:table_id>/update/", views.api_table_crud, name="api_table_update"),
    path("api/table/<int:table_id>/delete/", views.api_table_crud, name="api_table_delete"),
    path("api/layout/bulk-update/", views.api_bulk_update_layout, name="api_bulk_update_layout"),
    
    # Bookings
    path(
        "bookings/",
        views.bookings,
        name="bookings"
    ),

    path(
        "room-booking/<int:booking_id>/complete/",
        views.complete_room_booking,
        name="complete_room_booking"
    ),

    path(
        "table-booking/<int:booking_id>/complete/",
        views.complete_table_booking,
        name="complete_table_booking"
    ),

    # Reviews
    path("review/<int:restaurant_id>/", views.leave_review, name="leave_review"),
    path("review/<int:review_id>/edit/", views.edit_review, name="edit_review"),
    path("review/<int:review_id>/delete/", views.delete_review, name="delete_review"),

    path('api/booking-details/<str:booking_type>/<int:booking_id>/', views.api_booking_details, name='api_booking_details'),
]