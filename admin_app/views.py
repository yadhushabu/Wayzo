from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta

from destinations.models import DestinationPlace

User = get_user_model()

@login_required
def admin_dashboard(request):
    # Check if user is admin or superuser
    if request.user.role != 'admin' and not request.user.is_superuser:
        messages.error(request, "You don't have permission to access the admin dashboard.")
        return redirect('login')

    # Show only traveller, agency and restaurant
    users = User.objects.filter(
        role__in=['traveller', 'agency', 'restaurant']
    ).order_by('-date_joined')

    # Get statistics
    total_users = users.count()
    active_users = users.filter(is_active=True).count()
    inactive_users = total_users - active_users
    
    # Users joined in last 7 days
    last_week = timezone.now() - timedelta(days=7)
    new_users = users.filter(date_joined__gte=last_week).count()

    context = {
        'users': users,
        'total_users': total_users,
        'active_users': active_users,
        'inactive_users': inactive_users,
        'new_users': new_users,
    }

    return render(request, 'admin/dashboard.html', context)

from restaurants.models import RestaurantGallery

@login_required
def user_profile(request, user_id):

    if request.user.role != 'admin' and not request.user.is_superuser:
        messages.error(request, "You don't have permission.")
        return redirect('admin_app:admin_dashboard')

    user = get_object_or_404(User, id=user_id)

    agency_profile = None
    restaurantprofile = None
    gallery_images = None

    if user.role == 'agency':
        agency_profile = getattr(user, 'agencyprofile', None)

    if user.role == 'restaurant':
        restaurantprofile = getattr(user, 'restaurantprofile', None)

        if restaurantprofile:
            gallery_images = RestaurantGallery.objects.filter(
                restaurant=restaurantprofile
            )

    return render(request, 'admin/user_profile.html', {
        'profile_user': user,
        'agency_profile': agency_profile,
        'restaurantprofile': restaurantprofile,
        'gallery_images': gallery_images,
    })




@login_required
def toggle_user_status(request, user_id):
    # Check if user is admin or superuser
    if request.user.role != 'admin' and not request.user.is_superuser:
        messages.error(request, "You don't have permission to modify user status.")
        return redirect('admin_app:login')

    user = get_object_or_404(User, id=user_id)
    
    # Don't allow deactivating yourself
    if user.id == request.user.id:
        messages.error(request, "You cannot change your own status.")
        return redirect('user_profile', user_id=user.id)
    
    # Toggle status
    user.is_active = not user.is_active
    user.save()
    
    status = "activated" if user.is_active else "deactivated"
    messages.success(request, f'User {user.username} has been {status} successfully.')
    
    return redirect('admin_app:user_profile', user_id=user.id)


from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from accounts.models import CustomUser  # adjust if needed

@login_required
def toggle_verification(request, user_id):

    if request.user.role != 'admin' and not request.user.is_superuser:
        return redirect('login')

    user = get_object_or_404(User, id=user_id)

    if user.role == 'agency' and hasattr(user, 'agencyprofile'):

        profile = user.agencyprofile
        profile.is_approved = not profile.is_approved
        profile.save()

        # sync user verification
        user.is_verified = profile.is_approved
        user.save(update_fields=['is_verified'])

    elif user.role == 'restaurant' and hasattr(user, 'restaurantprofile'):

        profile = user.restaurantprofile
        profile.is_approved = not profile.is_approved
        profile.save()

        # sync user verification
        user.is_verified = profile.is_approved
        user.save(update_fields=['is_verified'])

    return redirect('admin_app:user_profile', user_id=user.id)





# @user_passes_test(lambda u: u.is_staff)
# def pending_places(request):

#     places = DestinationPlace.objects.filter(is_approved=False)

#     return render(request, "destinations/pending_places.html", {
#         "places": places
#     })

# @user_passes_test(lambda u: u.is_staff)
# def approve_place(request, place_id):

#     place = get_object_or_404(DestinationPlace, id=place_id)

#     place.is_approved = True
#     place.save()

#     return redirect("destinations:pending_places")