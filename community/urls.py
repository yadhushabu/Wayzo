from django.urls import path
from . import views
app_name = 'community'

urlpatterns = [

    # 🔹 Main
    path('home/', views.community_home, name="community_home"),

    # 🔹 Community CRUD
    path('', views.community_list, name="community_list"),
    path('create/', views.create_community, name="create_community"),
    path('<int:pk>/', views.community_detail, name="community_detail"),
    path('leave/<int:community_id>/', views.leave_community, name='leave_community'),

    # 🔹 Join / Requests
    path('join/<int:community_id>/', views.join_community, name="join_community"),
    path('accept-request/<int:request_id>/', views.accept_request, name="accept_request"),
    path('reject-request/<int:request_id>/', views.reject_request, name='reject_request'), 

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


    path('api/unread-notifications-count/', views.get_unread_notifications_count, name='unread_notifications_count'),
    path('api/recent-notifications/', views.get_recent_notifications, name='recent_notifications'),
    path('notification/mark-read/<int:notification_id>/', views.mark_notification_read, name='mark_notification_read'),
    path('notification/mark-all-read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
    
    path(
    'private-trip/create/',
    views.create_private_trip,
    name='create_private_trip'
),

path(
    'trip/join/<str:invite_code>/',
    views.join_private_trip,
    name='join_private_trip'
),

path(
    'trip/update-location/',
    views.update_location,
    name='update_location'
),

path(
    'trip/<int:trip_id>/locations/',
    views.get_trip_locations,
    name='get_trip_locations'),

    path('private-trip/list/', views.private_trip_list, name="private_trip_list"),
    path('trip/invite/<str:invite_code>/', views.invite_trip_page, name='invite_trip'),
    path(
    'trip/<int:trip_id>/live-map/',
    views.trip_live_map,
    name='trip_live_map'
),
    path('promote-to-coordinator/<int:participant_id>/', views.promote_to_coordinator, name='promote_to_coordinator'),


]