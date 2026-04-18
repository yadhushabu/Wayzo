from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from travellers.models import PropertyBooking
from .models import RestaurantGallery
from django.contrib import messages


@login_required
def restaurant_dashboard(request):

    restaurant = request.user.restaurantprofile
    images = RestaurantGallery.objects.filter(restaurant=restaurant)

    bookings = PropertyBooking.objects.filter(
    property=restaurant
).order_by('-created_at')

    return render(
        request,
        "restaurants/dashboard.html",
        {
            "restaurant": restaurant,
            "images": images,
            "bookings": bookings
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

    

    # ✅ GROUP IMAGES BY SECTION (IMPORTANT)
    grouped_images = [
    {
        "key": key,
        "label": label,
        "images": images.filter(section=key)
    }
    for key, label in RestaurantGallery.SECTION_CHOICES
]

    context = {
        "images": images,
        "sections": RestaurantGallery.SECTION_CHOICES,
        "grouped_images": grouped_images,
        "total_images": images.count(),
    }

    return render(request, "restaurants/manage_gallery.html", context)


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
        "restaurants/edit_profile.html",  # Make sure this matches your template path
        {
            "form": form,
            "user": user,
            "restaurant": restaurant,  # ← ADD THIS LINE - CRITICAL!
        }
    )

from django.shortcuts import get_object_or_404

@login_required
def delete_gallery_image(request, id):

    image = get_object_or_404(RestaurantGallery, id=id)

    if image.restaurant.user != request.user:
        return redirect("manage_gallery")

    image.delete()

    messages.success(request, "Image deleted successfully")

    return redirect("manage_gallery")

from django import template
register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)



@login_required
def confirm_booking(request, id):

    booking = get_object_or_404(PropertyBooking, id=id)

    if booking.property.user != request.user:
        return redirect("restaurant_dashboard")

    booking.status = "confirmed"
    booking.save()

    messages.success(request, "Booking confirmed ✅")
    return redirect("bookings")


@login_required
def reject_booking(request, id):

    booking = get_object_or_404(PropertyBooking, id=id)

    if booking.property.user != request.user:
        return redirect("restaurant_dashboard")

    booking.status = "rejected"
    booking.save()

    messages.error(request, "Booking rejected ❌")
    return redirect("bookings")

@login_required
def bookings(request):

    restaurant = request.user.restaurantprofile

    bookings = PropertyBooking.objects.filter(
        property=restaurant
    ).order_by('-created_at')

    return render(request, "restaurants/bookings.html", {
        "bookings": bookings
    })