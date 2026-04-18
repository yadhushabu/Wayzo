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
    path('wishlist/', views.wishlist, name='wishlist'),
    path('wishlist_add/<int:package_id>/', views.wishlist_add, name='wishlist_add'),
    path('booking/<int:id>/', views.book_package, name='book_package'),
    path('booking/cancel/<int:id>/', views.cancel_booking, name='cancel_booking'),
    path("wishlist/remove/<int:package_id>/", views.wishlist_remove, name="wishlist_remove"),
    path('pay-advance/<int:id>/', views.pay_advance, name='pay_advance'),
    path('pay-remaining/<int:id>/', views.pay_remaining, name='pay_remaining'),
    # path("plan-trip/", views.generate_trip_plan, name="plan_trip"),

    # Restaurant Booking
    path("book-property/<int:pk>/", views.book_property, name="book_property"),
    # Social Features
    path("follow/<int:user_id>/", views.toggle_follow, name="toggle_follow"),
    path('followers/<int:user_id>/', views.followers_list, name='followers_list'),
    path('following/<int:user_id>/', views.following_list, name='following_list'),
    
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

    path('invoice/<int:id>/', views.download_invoice, name='download_invoice'),
    path("plan/create/", views.create_travel_plan, name="create_travel_plan"),
    path("plans/", views.my_travel_plans, name="my_travel_plans"),
]