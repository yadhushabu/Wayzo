from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal

from planner.services.itinerary_generator import generator

from .models import CompletedTrip, ProfileComment, ProfilePost, ProfilePostLike, PropertyBooking,  TravellerProfile, Wishlist, Follow
from .forms import NewPostForm, TravellerProfileEditForm, PropertyBookingForm

from restaurants.models import RestaurantProfile
from agencies.models import TourPackage, PackageBooking, CancellationPolicy
from community.models import ChatRoom, Message, Notification, Post, Trip

User = get_user_model()

# ==================== DASHBOARD VIEW ====================
@login_required
def dashboard(request):
    """Main dashboard for logged-in users showing packages, restaurants, bookings + explore module"""

    profile = get_object_or_404(TravellerProfile, user=request.user)

    # Get data for dashboard
    packages = TourPackage.objects.filter(
        is_active=True,
        agency__is_approved=True
    ).select_related('agency__user')[:6]

    restaurants = RestaurantProfile.objects.filter(is_approved=True)[:6]

    bookings = PackageBooking.objects.filter(
        traveller=request.user
    ).order_by('-booked_at')[:5]

    # Stats
    wishlist_count = Wishlist.objects.filter(user=request.user).count()
    bookings_count = PackageBooking.objects.filter(traveller=request.user).count()
    posts_count = ProfilePost.objects.filter(user=request.user).count()



    context = {
        'profile': profile,

        # existing
        'packages': packages,
        'restaurants': restaurants,
        'bookings': bookings,

        # stats
        'wishlist_count': wishlist_count,
        'bookings_count': bookings_count,
        'posts_count': posts_count,



    }

    return render(request, "travellers/dashboard.html", context)


# ==================== USER PROFILE VIEW ====================
@login_required
def user_profile(request, user_id):
    """Own profile only"""

    user = get_object_or_404(User, id=user_id)

    # 🔥 redirect if trying to view others
    if request.user != user:
        return redirect("travellers:public_profile", user_id=user.id)

    profile = get_object_or_404(TravellerProfile, user=user)

    posts = ProfilePost.objects.filter(user=user).order_by("-created_at")
    trips = CompletedTrip.objects.filter(user=user, is_shared=True)

    followers_count = Follow.objects.filter(following=user).count()
    following_count = Follow.objects.filter(follower=user).count()

    context = {
        'profile_user': user,
        'profile': profile,
        'posts': posts,
        'trips': trips,
        'followers_count': followers_count,
        'following_count': following_count,
    }

    return render(request, "travellers/user_profile.html", context)

# ==================== RESTAURANT DETAIL ====================
def restaurant_detail(request, pk):
    restaurant = get_object_or_404(RestaurantProfile, id=pk)
    return render(request, "travellers/property_detail.html", {
        "restaurant": restaurant,
        "images": restaurant.gallery.all()
    })


# ==================== EDIT PROFILE ====================
@login_required
def edit_profile(request):
    profile = get_object_or_404(TravellerProfile, user=request.user)
    
    if request.method == "POST":
        form = TravellerProfileEditForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect("travellers:user_profile", user_id=request.user.id)
    else:
        form = TravellerProfileEditForm(instance=profile)
    
    return render(request, "travellers/edit_profile.html", {
        "form": form,
        "profile": profile
    })


# ==================== BOOKINGS ====================
@login_required
def my_bookings(request):
    package_bookings = PackageBooking.objects.filter(
        traveller=request.user
    ).select_related('package', 'package__agency').order_by('-booked_at')

    property_bookings = PropertyBooking.objects.filter(
        user=request.user
    ).select_related('property').order_by('-booking_date')

    for booking in package_bookings:

        # ✅ Ensure status never becomes None (important fix)
        if not booking.status:
            booking.status = "pending"

        # ✅ Default values to avoid template errors
        booking.refund_percentage = 0
        booking.refund_amount = 0

        # ✅ Calculate refund only if cancelled
        if booking.status == "cancelled":
            booking.refund_percentage = booking.get_refund_percentage()
            booking.refund_amount = booking.calculate_refund_amount()

        # ✅ Optional: calculate payment progress (for progress bar)
        if booking.total_amount:
            paid = 0

            if booking.payment_status == "partial":
                paid = booking.advance_amount or 0
            elif booking.payment_status == "paid":
                paid = booking.total_amount

            booking.payment_progress = int((paid / booking.total_amount) * 100)
        else:
            booking.payment_progress = 0

    return render(request, "travellers/my_bookings.html", {
        "package_bookings": package_bookings,
        "property_bookings": property_bookings
    })


# ==================== ALL RESTAURANTS ====================
def all_restaurants(request):
    restaurants = RestaurantProfile.objects.filter(is_approved=True)
    return render(request, "travellers/all_restaurants.html", {"restaurants": restaurants})


# ==================== ALL PACKAGES ====================
from django.core.paginator import Paginator
from django.db.models import Q, F, Value, FloatField
from django.db.models.functions import Coalesce
from django.db.models import ExpressionWrapper

@login_required
def all_packages(request):
    """Display all packages with categories, filters, sorting, and search"""
    
    profile = get_object_or_404(TravellerProfile, user=request.user)
    
    # Base queryset - only active packages
    packages = TourPackage.objects.filter(is_active=True)
    
    # Get filter parameters
    search_query = request.GET.get('search', '')
    category = request.GET.get('category', 'all')
    min_price = request.GET.get('min_price', '')
    max_price = request.GET.get('max_price', '')
    duration = request.GET.get('duration', '')
    transport = request.GET.get('transport', '')
    accommodation = request.GET.get('accommodation', '')
    language = request.GET.get('language', '')
    sort_by = request.GET.get('sort', 'featured')
    
    # ========== SEARCH ==========
    if search_query:
        packages = packages.filter(
            Q(title__icontains=search_query) |
            Q(places_covered__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # ========== CATEGORIES ==========
    if category == 'featured':
        packages = packages.filter(is_featured=True)
    elif category == 'budget':
        packages = packages.filter(
            Q(price__lte=15000) | Q(discounted_price__lte=12000)
        )
    elif category == 'honeymoon':
        packages = packages.filter(suitable_for__icontains='Honeymoon')
    elif category == 'family':
        packages = packages.filter(suitable_for__icontains='Family')
    elif category == 'adventure':
        packages = packages.filter(suitable_for__icontains='Adventure')
    elif category == 'relaxation':
        packages = packages.filter(suitable_for__icontains='Relaxation')
    elif category == 'city':
        packages = packages.filter(suitable_for__icontains='City Tour')
    
    # ========== PRICE FILTER ==========
    if min_price:
        packages = packages.filter(
            Q(discounted_price__gte=min_price) | 
            Q(price__gte=min_price, discounted_price__isnull=True)
        )
    if max_price:
        packages = packages.filter(
            Q(discounted_price__lte=max_price) | 
            Q(price__lte=max_price, discounted_price__isnull=True)
        )
    
    # ========== DURATION FILTER ==========
    if duration == 'short':
        packages = packages.filter(duration_days__lte=3)
    elif duration == 'medium':
        packages = packages.filter(duration_days__gte=4, duration_days__lte=7)
    elif duration == 'long':
        packages = packages.filter(duration_days__gte=8)
    
    # ========== TRANSPORT FILTER ==========
    if transport:
        packages = packages.filter(transport_type__icontains=transport)

    # ========== ACCOMMODATION FILTER ==========
    if accommodation:
        packages = packages.filter(accommodation_type__icontains=accommodation)

    # ========== LANGUAGE FILTER ==========
    if language:
        packages = packages.filter(guide_language__icontains=language)
    
    # ========== SORTING ==========
    if sort_by == 'price_low':
        packages = packages.annotate(
            effective_price=Coalesce('discounted_price', 'price')
        ).order_by('effective_price')
    elif sort_by == 'price_high':
        packages = packages.annotate(
            effective_price=Coalesce('discounted_price', 'price')
        ).order_by('-effective_price')
    elif sort_by == 'new':
        packages = packages.order_by('-created_at')
    elif sort_by == 'discount':
        packages = packages.filter(discounted_price__isnull=False).order_by('-discount_percentage')
    else:
        packages = packages.order_by('-is_featured', '-created_at')
    
    # ========== PAGINATION ==========
    paginator = Paginator(packages, 9)
    page_number = request.GET.get('page')
    packages_page = paginator.get_page(page_number)
    
    # Get unread notifications count
    unread_notifications = Notification.objects.filter(user=request.user, is_read=False).count()
    
    context = {
        'profile': profile,
        'packages': packages_page,
        'unread_notifications': unread_notifications,
        'current_category': category,
        'current_sort': sort_by,
    }
    
    return render(request, 'travellers/all_packages.html', context)


# ==================== PACKAGE DETAIL ====================
def package_detail(request, id):
    package = get_object_or_404(TourPackage, id=id, is_active=True)
    
    itineraries = package.itineraries.all().order_by('day_number')
    images = package.images.all()
    
    # Check wishlist
    is_wishlisted = False
    if request.user.is_authenticated:
        is_wishlisted = Wishlist.objects.filter(
            user=request.user,
            package=package
        ).exists()
    
    # Calculate booking window
    today = timezone.now().date()
    min_booking_days = package.min_booking_days or 1
    max_booking_days = package.max_booking_days or 365
    
    earliest_booking_date = today + timedelta(days=min_booking_days)
    latest_booking_date = today + timedelta(days=max_booking_days)
    
    # Get cancellation policies
    cancellation_policies = package.cancellation_policies.all().order_by('-days_before')
    
    context = {
        "package": package,
        "itineraries": itineraries,
        "images": images,
        "is_wishlisted": is_wishlisted,
        "earliest_booking_date": earliest_booking_date,
        "latest_booking_date": latest_booking_date,
        "min_booking_days": min_booking_days,
        "max_booking_days": max_booking_days,
        "cancellation_policies": cancellation_policies,
    }
    
    return render(request, "travellers/package_detail.html", context)


# ==================== BOOK PACKAGE ====================
@login_required
def book_package(request, id):
    package = get_object_or_404(TourPackage, id=id)
    
    # Check if package is active
    if not package.is_active:
        messages.error(request, "This package is currently not available for booking.")
        return redirect('travellers:all_packages')
    
    if request.method == "POST":
        try:
            travellers_count = request.POST.get("travellers_count")
            travel_date_str = request.POST.get("travel_date")
            
            # Validate travellers count
            if not travellers_count:
                messages.error(request, "Please enter number of travellers.")
                return redirect('travellers:book_package', id=package.id)
            
            travellers_count = int(travellers_count)
            
            # Check group size limits
            if package.min_group_size and travellers_count < package.min_group_size:
                messages.error(request, f"Minimum {package.min_group_size} travellers required for this package.")
                return redirect('travellers:book_package', id=package.id)
            
            if package.max_group_size and travellers_count > package.max_group_size:
                messages.error(request, f"Maximum {package.max_group_size} travellers allowed for this package.")
                return redirect('travellers:book_package', id=package.id)
            
            # Validate travel date
            if not travel_date_str:
                messages.error(request, "Please select a travel date.")
                return redirect('travellers:book_package', id=package.id)
            
            travel_date = datetime.strptime(travel_date_str, '%Y-%m-%d').date()
            today = timezone.now().date()
            
            # Check if travel date is in the past
            if travel_date < today:
                messages.error(request, "Travel date cannot be in the past. Please select a future date.")
                return redirect('travellers:book_package', id=package.id)
            
            # Check minimum booking days restriction
            min_booking_days = package.min_booking_days or 1
            days_before_travel = (travel_date - today).days
            
            if days_before_travel < min_booking_days:
                messages.error(
                    request, 
                    f"This package requires booking at least {min_booking_days} days in advance. "
                    f"Please select a travel date that is at least {min_booking_days} days from today."
                )
                return redirect('travellers:book_package', id=package.id)
            
            # Check maximum booking days restriction
            max_booking_days = package.max_booking_days or 365
            if days_before_travel > max_booking_days:
                messages.error(
                    request, 
                    f"This package can only be booked up to {max_booking_days} days in advance. "
                    f"Please select a closer travel date."
                )
                return redirect('travellers:book_package', id=package.id)
            
            # Calculate pricing
            price_per_person = package.discounted_price if package.discounted_price else package.price
            total_amount = price_per_person * Decimal(str(travellers_count))
            
            # Calculate advance (30% of total)
            advance_amount = total_amount * Decimal('0.3')
            remaining_amount = total_amount - advance_amount
            
            # Create booking
            booking = PackageBooking.objects.create(
                package=package,
                traveller=request.user,
                travellers_count=travellers_count,
                travel_date=travel_date,
                status="pending",
                total_amount=total_amount,
                advance_amount=advance_amount,
                remaining_amount=remaining_amount,
                payment_status="pending"
            )
            
            # Notify agency
            Notification.objects.create(
                user=package.agency.user,
                notification_type="booking",
                message=f"New booking request from {request.user.get_full_name() or request.user.username} for {package.title} - {travellers_count} travellers - ₹{total_amount:,.2f}"
            )
            
            # Notify traveller
            Notification.objects.create(
                user=request.user,
                notification_type="booking",
                message=f"Booking request sent for {package.title} on {travel_date.strftime('%d %b, %Y')}. Total: ₹{total_amount:,.2f} (Advance: ₹{advance_amount:,.2f})"
            )
            
            messages.success(
                request, 
                f"Booking request sent successfully! Total amount: ₹{total_amount:,.2f}. "
                f"Please pay advance of ₹{advance_amount:,.2f} to confirm your booking."
            )
            
            return redirect("travellers:my_bookings")
            
        except ValueError as e:
            messages.error(request, f"Invalid input: {str(e)}")
            return redirect('travellers:book_package', id=package.id)
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
            return redirect('travellers:book_package', id=package.id)
    
    # GET request - show booking form
    today = timezone.now().date()
    min_booking_days = package.min_booking_days or 1
    max_booking_days = package.max_booking_days or 365
    
    earliest_date = today + timedelta(days=min_booking_days)
    latest_date = today + timedelta(days=max_booking_days)
    
    # Price information
    original_price = package.price
    discounted_price = package.discounted_price
    price_per_person = discounted_price if discounted_price else original_price
    has_discount = discounted_price and discounted_price < original_price
    
    # Get cancellation policies
    cancellation_policies = package.cancellation_policies.all().order_by('-days_before')
    
    context = {
        "package": package,
        "earliest_date": earliest_date,
        "latest_date": latest_date,
        "min_travellers": package.min_group_size or 1,
        "max_travellers": package.max_group_size or 10,
        "price_per_person": price_per_person,
        "original_price": original_price,
        "has_discount": has_discount,
        "discount_percentage": package.discount_percentage,
        "cancellation_policies": cancellation_policies,
        "min_booking_days": min_booking_days,
        "max_booking_days": max_booking_days,
    }
    
    return render(request, "travellers/book_package.html", context)


# ==================== CANCEL BOOKING ====================
@login_required
def cancel_booking(request, id):
    booking = get_object_or_404(
        PackageBooking,
        id=id,
        traveller=request.user
    )

    # ✅ Allow cancel only if not already cancelled
    if booking.status in ["pending", "approved"]:

        # ✅ mark who cancelled
        booking.cancelled_by = "user"

        # ✅ calculate refund using model logic
        refund_amount = booking.calculate_refund_amount()
        refund_percentage = booking.get_refund_percentage()

        # ✅ update booking
        booking.status = "cancelled"
        booking.save()

        # ✅ notify agency
        Notification.objects.create(
            user=booking.package.agency.user,
            notification_type="booking",
            message=(
                f"Booking cancelled by {request.user.get_full_name() or request.user.username} "
                f"for {booking.package.title}. Refund: ₹{refund_amount:,.2f} ({refund_percentage}%)"
            )
        )

        # ✅ notify traveller
        Notification.objects.create(
            user=request.user,
            notification_type="booking",
            message=(
                f"Your booking for {booking.package.title} has been cancelled. "
                f"Refund: ₹{refund_amount:,.2f} ({refund_percentage}%)"
            )
        )

        messages.success(
            request,
            f"Booking cancelled successfully. Refund ₹{refund_amount:,.2f} ({refund_percentage}%)"
        )

    else:
        messages.error(request, "This booking cannot be cancelled.")

    return redirect("travellers:my_bookings")


# ==================== WISHLIST ====================
@login_required
def wishlist_add(request, package_id):
    package = get_object_or_404(TourPackage, id=package_id)
    wishlist_item = Wishlist.objects.filter(user=request.user, package=package)
    
    if wishlist_item.exists():
        wishlist_item.delete()
        status = 'removed'
    else:
        Wishlist.objects.create(user=request.user, package=package)
        status = 'added'
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': status})
    
    return redirect('travellers:wishlist')


@login_required
def wishlist_remove(request, package_id):
    wishlist_item = Wishlist.objects.filter(
        user=request.user,
        package_id=package_id
    ).first()
    
    if wishlist_item:
        wishlist_item.delete()
        messages.success(request, "Package removed from wishlist.")
    
    return redirect("travellers:wishlist")


@login_required
def wishlist(request):
    items = Wishlist.objects.filter(user=request.user).select_related('package', 'package__agency')
    return render(request, "travellers/wishlist.html", {"items": items})


# ==================== CHANGE PASSWORD ====================
@login_required
def change_password(request):
    if request.method == "POST":
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Password updated successfully ✅")
        else:
            messages.error(request, "Please fix the errors ❌")
    else:
        form = PasswordChangeForm(user=request.user)
    
    return render(request, 'travellers/change_password.html', {'form': form})


def change_email(request):
    return render(request, "travellers/change_email.html")


# ==================== FOLLOW SYSTEM ====================
@login_required
def toggle_follow(request, user_id):
    user_to_follow = get_object_or_404(User, id=user_id)
    
    if user_to_follow == request.user:
        messages.warning(request, "You cannot follow yourself.")
        return redirect("travellers:user_profile", user_id=user_id)
    
    follow, created = Follow.objects.get_or_create(
        follower=request.user,
        following=user_to_follow
    )
    
    if not created:
        follow.delete()
        messages.info(request, f"Unfollowed {user_to_follow.get_full_name() or user_to_follow.username}")
        
        # Notify when unfollowed? Optional
    else:
        messages.success(request, f"Now following {user_to_follow.get_full_name() or user_to_follow.username}")
        
        # Create notification for the user being followed
        Notification.objects.create(
            user=user_to_follow,
            notification_type="follow",
            message=f"{request.user.get_full_name() or request.user.username} started following you"
        )
    
    return redirect("travellers:user_profile", user_id=user_id)


def followers_list(request, user_id):
    user = get_object_or_404(User, id=user_id)
    followers = Follow.objects.filter(following=user).select_related("follower")
    return render(request, 'travellers/followers_list.html', {
        'profile_user': user,
        'followers': followers
    })


def following_list(request, user_id):
    user = get_object_or_404(User, id=user_id)
    following = Follow.objects.filter(follower=user).select_related("following")
    return render(request, 'travellers/following_list.html', {
        'profile_user': user,
        'following': following
    })


# ==================== POST SYSTEM ====================
@login_required
def new_post(request):
    if request.method == "POST":
        form = NewPostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.user = request.user
            post.save()
            messages.success(request, "Post created successfully!")
            return redirect('travellers:user_profile', user_id=request.user.id)
    else:
        form = NewPostForm()
    
    return render(request, 'travellers/new_post.html', {'form': form})


@login_required
def edit_post(request, post_id):
    post = get_object_or_404(ProfilePost, id=post_id)
    
    if post.user != request.user:
        messages.error(request, "You don't have permission to edit this post.")
        return redirect('travellers:user_profile', user_id=request.user.id)
    
    if request.method == "POST":
        form = NewPostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()
            messages.success(request, "Post updated successfully!")
            return redirect('travellers:user_profile', user_id=request.user.id)
    else:
        form = NewPostForm(instance=post)
    
    return render(request, 'travellers/edit_post.html', {'form': form})


@login_required
def delete_post(request, post_id):
    post = get_object_or_404(ProfilePost, id=post_id)
    
    if post.user == request.user:
        post.delete()
        messages.success(request, "Post deleted successfully!")
    else:
        messages.error(request, "You don't have permission to delete this post.")
    
    return redirect('travellers:user_profile', user_id=request.user.id)


@login_required
def like_profile_post(request, post_id):
    post = get_object_or_404(ProfilePost, id=post_id)
    
    like, created = ProfilePostLike.objects.get_or_create(
        user=request.user,
        post=post
    )
    
    if not created:
        like.delete()
        liked = False
    else:
        liked = True
        if post.user != request.user:
            Notification.objects.create(
                user=post.user,
                notification_type="post_like",
                message=f"{request.user.get_full_name() or request.user.username} liked your post"
            )
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'liked': liked,
            'likes_count': post.likes.count()
        })
    
    return redirect(request.META.get('HTTP_REFERER', 'travellers:dashboard'))


@login_required
def add_profile_comment(request, post_id):
    post = get_object_or_404(ProfilePost, id=post_id)
    
    if request.method == "POST":
        text = request.POST.get("text")
        
        if text and text.strip():
            comment = ProfileComment.objects.create(
                post=post,
                user=request.user,
                text=text.strip()
            )
            
            if post.user != request.user:
                Notification.objects.create(
                    user=post.user,
                    notification_type="comment",
                    message=f"{request.user.get_full_name() or request.user.username} commented on your post"
                )
            
            messages.success(request, "Comment added successfully!")
        else:
            messages.error(request, "Comment cannot be empty.")
    
    return redirect(request.META.get('HTTP_REFERER', 'travellers:dashboard'))


# ==================== INBOX ====================
@login_required
def inbox(request):
    rooms = ChatRoom.objects.filter(
        participants=request.user
    ).order_by("-created_at")
    
    user_id = request.GET.get("user_id")
    if user_id:
        other_user = get_object_or_404(User, id=user_id)
        room = ChatRoom.objects.filter(
            type='dm',
            participants=request.user
        ).filter(
            participants=other_user
        ).distinct().first()
        
        if not room:
            room = ChatRoom.objects.create(type='dm')
            room.participants.add(request.user, other_user)
        
        return redirect(f"{request.path}?room={room.id}")
    
    selected_room_id = request.GET.get("room")
    selected_room = None
    messages_list = []
    
    if selected_room_id:
        selected_room = get_object_or_404(ChatRoom, id=selected_room_id)
        if request.user not in selected_room.participants.all():
            return HttpResponseForbidden()
        messages_list = selected_room.messages.select_related("sender").order_by("created_at")
    
    if request.method == "POST":
        text = request.POST.get("message")
        if text and text.strip() and selected_room:
            Message.objects.create(
                room=selected_room,
                sender=request.user,
                text=text.strip()
            )
            return redirect(f"{request.path}?room={selected_room.id}")
    
    return render(request, "chat/inbox.html", {
        "rooms": rooms,
        "selected_room": selected_room,
        "messages": messages_list
    })


# ==================== PROPERTY BOOKING ====================
@login_required
def book_property(request, pk):
    property_obj = get_object_or_404(RestaurantProfile, id=pk)
    
    if request.method == "POST":
        form = PropertyBookingForm(request.POST)
        
        if form.is_valid():
            booking = form.save(commit=False)
            booking.user = request.user
            booking.property = property_obj
            
            if property_obj.property_type in ["Restaurant", "Cafe"]:
                booking.booking_type = "table"
                booking.check_in = None
                booking.check_out = None
                booking.rooms = None
            else:
                booking.booking_type = "room"
                booking.time = None
            
            booking.save()
            
            # Notify property owner
            Notification.objects.create(
                user=property_obj.user,
                notification_type="booking",
                message=f"New booking request from {request.user.get_full_name() or request.user.username} for {property_obj.name}"
            )
            
            messages.success(request, "Booking request sent successfully!")
            return redirect("travellers:my_bookings")
        else:
            messages.error(request, "Please correct the errors below.")
    
    else:
        form = PropertyBookingForm()
    
    return render(request, "travellers/book_property.html", {
        "form": form,
        "property": property_obj
    })


@login_required
def pay_advance(request, id):
    booking = get_object_or_404(PackageBooking, id=id, traveller=request.user)

    if booking.payment_status == "pending":
        booking.payment_status = "partial"
        booking.save()

        Notification.objects.create(
            user=request.user,
            notification_type="payment",
            message=f"Advance payment received for {booking.package.title}. Booking confirmed ✅"
        )

        messages.success(request, "Advance paid successfully. Booking confirmed!")

    return redirect("travellers:my_bookings")


@login_required
def pay_remaining(request, id):
    booking = get_object_or_404(
        PackageBooking,
        id=id,
        traveller=request.user
    )

    # ❌ Only allow after agency approval
    if booking.status != "confirmed":
        messages.error(request, "You can pay remaining only after booking is approved.")
        return redirect("travellers:my_bookings")

    # ❌ Must have paid advance first
    if booking.payment_status != "partial":
        messages.error(request, "Please pay advance first.")
        return redirect("travellers:my_bookings")

    # ❌ Prevent duplicate payment
    if booking.payment_status == "paid":
        messages.warning(request, "Remaining amount already paid.")
        return redirect("travellers:my_bookings")

    # ✅ Process payment (Demo)
    booking.payment_status = "paid"
    booking.remaining_amount = 0
    booking.save()

    # 🔔 Notify traveller
    Notification.objects.create(
        user=request.user,
        notification_type="payment",
        message=f"Full payment completed for {booking.package.title} 🎉"
    )

    # 🔔 Notify agency (optional but recommended)
    Notification.objects.create(
        user=booking.package.agency.user,
        notification_type="payment",
        message=f"{request.user.username} completed full payment for {booking.package.title}"
    )

    messages.success(request, "Remaining amount paid successfully!")

    return redirect("travellers:my_bookings")


from django.http import HttpResponse

@login_required
def download_invoice(request, id):
    booking = get_object_or_404(PackageBooking, id=id, traveller=request.user)

    content = f"""
    INVOICE

    Package: {booking.package.title}
    Travellers: {booking.travellers_count}
    Total: ₹{booking.total_amount}
    Paid: {booking.payment_status}
    """

    response = HttpResponse(content, content_type='text/plain')
    response['Content-Disposition'] = f'attachment; filename=invoice_{booking.id}.txt'

    return response



@login_required
def public_profile(request, user_id):
    """Public profile view for other travellers"""

    user = get_object_or_404(User, id=user_id)
    profile = get_object_or_404(TravellerProfile, user=user)

    # 🚫 Prevent accessing own profile here
    if request.user == user:
        return redirect("travellers:user_profile", user_id=user.id)

    # Posts
    posts = ProfilePost.objects.filter(user=user).order_by("-created_at")

    # Trips
    trips = CompletedTrip.objects.filter(user=user, is_shared=True)

    # Follow system
    followers_count = Follow.objects.filter(following=user).count()
    following_count = Follow.objects.filter(follower=user).count()

    is_following = Follow.objects.filter(
        follower=request.user,
        following=user
    ).exists()

    context = {
        'profile_user': user,
        'profile': profile,
        'posts': posts,
        'trips': trips,
        'followers_count': followers_count,
        'following_count': following_count,
        'is_following': is_following,
    }

    return render(request, "travellers/public_profile.html", context)



