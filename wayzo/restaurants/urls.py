from django.urls import path
from . import views

urlpatterns = [

    path("dashboard/", views.restaurant_dashboard, name="restaurant_dashboard"),
    path("edit-profile/", views.edit_restaurantprofile, name="edit_restaurantprofile"),
    path("manage_gallery/", views.manage_gallery, name="manage_gallery"),
    

]