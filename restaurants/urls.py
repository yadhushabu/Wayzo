from django.urls import path
from . import views

urlpatterns = [

    path("dashboard/", views.restaurant_dashboard, name="restaurant_dashboard"),
    path("edit-profile/", views.edit_restaurantprofile, name="edit_restaurantprofile"),
    path("manage_gallery/", views.manage_gallery, name="manage_gallery"),
    path("delete-gallery-image/<int:id>/",views.delete_gallery_image,name="delete_gallery_image"),
    path("confirm-booking/<int:id>/", views.confirm_booking, name="confirm_booking"),
    path("reject-booking/<int:id>/", views.reject_booking, name="reject_booking"),
    path("bookings/", views.bookings, name="bookings")
    

]