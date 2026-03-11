from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .models import RestaurantGallery
from django.contrib import messages

@login_required
def restaurant_dashboard(request):

    restaurant = request.user.restaurantprofile
    images = RestaurantGallery.objects.filter(restaurant=restaurant)

    return render(
        request,
        "restaurants/dashboard.html",
        {
            "restaurant": restaurant,
            "images": images
        }
    )

@login_required
def manage_gallery(request):

    restaurant = request.user.restaurantprofile

    if request.method == "POST":

        section = request.POST.get("section")
        images = request.FILES.getlist("image")

        for img in images:
            RestaurantGallery.objects.create(
                restaurant=restaurant,
                section=section,
                image=img
            )

        messages.success(request, "Images uploaded successfully")

        return redirect("manage_gallery")

    images = restaurant.gallery.all()

    return render(
        request,
        "restaurants/manage_gallery.html",
        {"images": images}
    )

from .forms import RestaurantProfileEditForm
from django.shortcuts import redirect

@login_required
def edit_restaurantprofile(request):

    restaurant = request.user.restaurantprofile
    user = request.user

    if request.method == "POST":

        form = RestaurantProfileEditForm(
            request.POST,
            request.FILES,
            instance=restaurant
        )

        profile_picture = request.FILES.get("profile_picture")

        if form.is_valid():

            form.save()

            if profile_picture:
                user.profile_picture = profile_picture
                user.save()

            return redirect("restaurant_dashboard")

    else:
        form = RestaurantProfileEditForm(instance=restaurant)

    return render(
        request,
        "restaurants/edit_profile.html",
        {
            "form": form,
            "user": user
        }
    )

