from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

app_name = "travellers"

urlpatterns = [
    # Dashboard - Main landing page after login
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # User Profile
    path('profile/<int:user_id>/', views.user_profile, name='user_profile'),
    path("traveller/<int:user_id>/", views.public_profile, name="public_profile"),
    
    # Edit Profile
    path('edit_profile/', views.edit_profile, name='edit_profile'),
    
    # Restaurants
    path("restaurant/<int:pk>/", views.restaurant_detail, name="restaurant_detail"),
    path("restaurants/", views.all_restaurants, name="all_restaurants"),
    
    # Packages
    path("packages/", views.all_packages, name="all_packages"),
    path("book/<int:id>/", views.book_package, name="book_package"),
    path('package/<int:id>/', views.package_detail, name='package_detail'),
    
    # Bookings & Wishlist
    path("my-bookings/", views.my_bookings, name="my_bookings"),
    path('booking/<int:id>/', views.book_package, name='book_package'),
    path('cancel-booking/<str:booking_type>/<int:booking_id>/', views.cancel_booking, name='cancel_booking'),
    path(
        "pay-advance/<int:id>/",
        views.pay_advance,
        name="pay_advance"
    ),

    path(
        "advance-success/<int:id>/",
        views.advance_payment_success,
        name="advance_payment_success"
    ),

    path(
        "pay-remaining/<int:id>/",
        views.pay_remaining,
        name="pay_remaining"
    ),

    path(
        "remaining-success/<int:id>/",
        views.remaining_payment_success,
        name="remaining_payment_success"
    ),

    path(
        "payment-success/",
        views.payment_success_page,
        name="payment_success_page"
    ),

    # Wishlist URLs
    path('wishlist/', views.wishlist, name='wishlist'),
    
    # Add to wishlist
    path('wishlist/add/package/<int:pk>/', views.wishlist_add_package, name='wishlist_add_package'),
    path('wishlist/add/restaurant/<int:pk>/', views.wishlist_add_restaurant, name='wishlist_add_restaurant'),
    
    # Remove from wishlist
    path('wishlist/remove/package/<int:pk>/', views.wishlist_remove_package, name='wishlist_remove_package'),
    path('wishlist/remove/restaurant/<int:pk>/', views.wishlist_remove_restaurant, name='wishlist_remove_restaurant'),
    
    # Legacy URLs (for backward compatibility)
    path('wishlist/add/<int:item_id>/', views.wishlist_add, {'item_type': 'package'}, name='wishlist_add'),
    path('wishlist/remove/<int:item_id>/', views.wishlist_remove, {'item_type': 'package'}, name='wishlist_remove'),


    # Restaurant Booking
    path('book-table/<int:pk>/', views.book_table, name='book_table'),
    path('book-room/<int:pk>/', views.book_room, name='book_room'),


      # Payment URLs
    path('room-payment/<int:booking_id>/', views.room_booking_payment, name='room_booking_payment'),
    path('table-payment/<int:booking_id>/', views.table_booking_payment, name='table_booking_payment'),
    path('room-payment-success/<int:booking_id>/', views.room_payment_success, name='room_payment_success'),
    path('table-payment-success/<int:booking_id>/', views.table_payment_success, name='table_payment_success'),
    
    # API endpoints
    path('api/table-slots/', views.api_table_slots, name='api_table_slots'),
    path('select-table/<int:pk>/', views.select_table, name='select_table'),
    path('api/table/<int:table_id>/details/', views.api_table_details, name='api_table_details'),
    path('api/table/book/', views.book_table_from_layout, name='book_table_from_layout'),

    # Social Features
    path("follow/<int:user_id>/", views.toggle_follow, name="toggle_follow"),
    path(
        "followers/<int:user_id>/",
        views.follow_list,
        {"mode": "followers"},
        name="followers_list"
    ),

    path(
        "following/<int:user_id>/",
        views.follow_list,
        {"mode": "following"},
        name="following_list"
    ),
    path('api/search-travellers/', views.search_travellers_api, name='search_travellers_api'),
    path('search-travellers/', views.search_travellers_page, name='search_travellers'),
    
    # Posts
    path('post/new/', views.new_post, name='new_post'),
    path('post/<int:post_id>/edit/', views.edit_post, name='edit_post'),
    path('post/<int:post_id>/delete/', views.delete_post, name='delete_post'),
    path('like-profile-post/<int:post_id>/', views.like_profile_post, name='like_profile_post'),
    path('comment-profile-post/<int:post_id>/', views.add_profile_comment, name='add_profile_comment'),
    
    # Account Settings
    path('change-password/', views.change_password, name='change_password'),
    path("change-email/", views.change_email, name="change_email"),
    
    # Messaging
    path("inbox/", views.inbox, name="inbox"),
    path('send-message-api/', views.send_message_api, name='send_message_api'),

    path('invoice/<int:id>/', views.download_invoice, name='download_invoice'),

    path("buddy/send/<int:user_id>/", views.send_buddy_request, name="send_buddy_request"),
    path("buddy/accept/<int:request_id>/", views.accept_buddy_request, name="accept_buddy_request"),
    path("buddy/reject/<int:request_id>/", views.reject_buddy_request, name="reject_buddy_request"),
    path("buddy/cancel/<int:request_id>/", views.cancel_buddy_request, name="cancel_buddy_request"),
    path("buddy/requests/", views.buddy_requests, name="buddy_requests"),
    path("buddy/remove/<int:user_id>/", views.remove_buddy, name="remove_buddy"),



    path(
    'review/<int:booking_id>/',
    views.add_package_review,
    name='add_package_review'
),
    path("agency/<int:agency_id>/", views.agency_detail, name="agency_detail"),



]