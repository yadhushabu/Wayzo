from django.urls import path
from . import views

urlpatterns = [

    # 🔹 Main
    path('home/', views.community_home, name="community_home"),

    # 🔹 Community CRUD
    path('', views.community_list, name="community_list"),
    path('create/', views.create_community, name="create_community"),
    path('<int:pk>/', views.community_detail, name="community_detail"),

    # 🔹 Join / Requests
    path('join/<int:community_id>/', views.join_community, name="join_community"),
    path('accept-request/<int:request_id>/', views.accept_request, name="accept_request"),

    # 🔹 Posts & Trips
    path('<int:community_id>/post/', views.create_post, name="create_post"),
    path('<int:community_id>/trip/', views.create_trip, name="create_trip"),
    path('join-trip/<int:trip_id>/', views.join_trip, name="join_trip"),

    # 🔹 User sections
    path('notifications/', views.notifications_view, name="notifications"),
    path('like-post/<int:post_id>/', views.like_post, name='like_post'),
    path('add-comment/<int:post_id>/', views.add_comment, name='add_comment'),
    path('edit/<int:community_id>/', views.edit_community, name="edit_community"),
    path('delete/<str:item_type>/<int:item_id>/', views.delete_item, name='delete_item'),
    path('<int:community_id>/members/', views.community_members, name="community_members"),
    path("delete-community/<int:community_id>/", views.delete_community, name="delete_community"),
    path("poll/vote/<int:option_id>/", views.vote_poll, name="vote_poll"),
    path("<int:community_id>/poll/",views.create_poll,name="create_poll"),
    path('trip/<int:id>/', views.trip_detail, name='trip_detail'),
    path('trip/<int:trip_id>/cancel/', views.cancel_trip, name='cancel_trip'),
    path('trip/<int:trip_id>/edit/', views.edit_trip, name='edit_trip'),
    path('trip/<int:trip_id>/chat/', views.trip_chat, name='trip_chat'),
    path("approve/<int:participant_id>/", views.approve_participant, name="approve_participant"),
    path('reject/<int:participant_id>/', views.reject_participant, name='reject_participant'),
    path('remove/<int:participant_id>/', views.remove_participant, name='remove_participant'),

    

]