import razorpay
from django.conf import settings

from admin_app.utils import create_audit_log

client = razorpay.Client(
    auth=(
        settings.RAZORPAY_KEY_ID,
        settings.RAZORPAY_KEY_SECRET
    )
)

from restaurants.models import Payment as RestaurantPayment
from agencies.models import Payment as AgencyPayment
from django.db import models
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.urls import reverse
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from django.views.decorators.http import require_http_methods
from planner.services.itinerary_generator import generator
from wayzo import settings

from .models import BuddyRequest, CompletedTrip, ProfileComment, ProfilePost, ProfilePostLike, TravellerProfile, Wishlist, Follow
from .forms import NewPostForm, TravellerProfileEditForm

from restaurants.models import RestaurantProfile, Room, RoomBooking, RoomType, Table, TableBooking
from agencies.models import PackageReview, TourPackage, PackageBooking, CancellationPolicy
from community.models import ChatRoom, Message, Notification, Post, Trip, TripParticipant
from destinations.models import Destination
from agencies.utils import auto_cancel_expired_bookings, generate_invoice_pdf

User = get_user_model()

# ==================== DASHBOARD VIEW ====================
@login_required
def dashboard(request):
    """Main dashboard for logged-in users showing packages, restaurants, destinations, bookings + explore module"""
    auto_cancel_expired_bookings()

    profile = get_object_or_404(TravellerProfile, user=request.user)

    # Universal search
    search_query = request.GET.get('search', '').strip()

    # Get data for dashboard
    packages = TourPackage.objects.filter(
        is_active=True,
        agency__is_approved=True
    ).select_related('agency__user')[:6]

    restaurants = RestaurantProfile.objects.filter(is_approved=True)[:6]
    
    # Get destinations for dashboard - Use the correct field name 'final_trending_score'
    destinations = Destination.objects.filter(
        is_approved=True
    ).order_by("-final_trending_score", "-average_rating", '-created_at')[:3]

    bookings = PackageBooking.objects.filter(
        traveller=request.user
    ).order_by('-booked_at')[:5]

    # Stats
    wishlist_count = Wishlist.objects.filter(user=request.user).count()
    bookings_count = PackageBooking.objects.filter(traveller=request.user).count()
    posts_count = ProfilePost.objects.filter(user=request.user).count()
    
    # Notification count
    from community.models import Notification
    unread_notifications = Notification.objects.filter(
        user=request.user, 
        is_read=False
    ).count()
    
    # Get buddy pending count for sidebar badge
    from .models import BuddyRequest
    buddy_pending_count = BuddyRequest.objects.filter(
        to_user=request.user, 
        status='pending'
    ).count()

    # Universal search results
    search_destinations = []
    search_packages = []
    search_restaurants = []

    if search_query:
        from django.db.models import Q

        search_destinations = Destination.objects.filter(
            is_approved=True
        ).filter(
            Q(name__icontains=search_query) |
            Q(city__icontains=search_query) |
            Q(country__icontains=search_query) |
            Q(description__icontains=search_query)
        ).order_by('-final_trending_score', '-average_rating')[:6]

        search_packages = TourPackage.objects.filter(
            is_active=True,
            agency__is_approved=True
        ).filter(
            Q(title__icontains=search_query) |
            Q(places_covered__icontains=search_query) |
            Q(description__icontains=search_query)
        ).select_related('agency__user')[:6]

        search_restaurants = RestaurantProfile.objects.filter(
            is_approved=True
        ).filter(
            Q(restaurant_name__icontains=search_query) |
            Q(city__icontains=search_query) |
            Q(state__icontains=search_query) |
            Q(description__icontains=search_query)
        )[:6]

    context = {
        'profile': profile,
        
        # Dashboard data
        'packages': packages,
        'restaurants': restaurants,
        'destinations': destinations,
        'bookings': bookings,
        
        # Stats
        'wishlist_count': wishlist_count,
        'bookings_count': bookings_count,
        'posts_count': posts_count,
        
        # Notifications
        'unread_notifications': unread_notifications,
        'buddy_pending_count': buddy_pending_count,

        # Universal search
        'search_query': search_query,
        'search_destinations': search_destinations,
        'search_packages': search_packages,
        'search_restaurants': search_restaurants,
    }

    return render(request, "travellers/dashboard.html", context)


# ==================== USER PROFILE VIEW ====================

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.models import CustomUser  # Import your custom user model
from .models import TravellerProfile, ProfilePost, CompletedTrip, Follow

@login_required
def user_profile(request, user_id):
    """Own profile only - using custom user model"""
    
    # Use CustomUser instead of User
    user = get_object_or_404(CustomUser, id=user_id)
    is_owner = request.user.id == user_id

    # Redirect if trying to view others
    if request.user != user:
        return redirect("travellers:public_profile", user_id=user.id)

    # Get profile (create if doesn't exist)
    profile, created = TravellerProfile.objects.get_or_create(
        user=user,
        defaults={
            'first_name': user.first_name or '',
            'last_name': user.last_name or '',
            'email': user.email or ''
        }
    )

    # Get posts
    posts = ProfilePost.objects.filter(user=user).order_by("-created_at")
    
    # Get trips
    trips = CompletedTrip.objects.filter(user=user, is_shared=True)
    
    # Get followers/following counts
    followers_count = Follow.objects.filter(following=user).count()
    following_count = Follow.objects.filter(follower=user).count()

    context = {
        'profile_user': user,
        'profile': profile,
        'posts': posts,
        'trips': trips,
        'followers_count': followers_count,
        'following_count': following_count,
        'is_owner': is_owner,
    }

    return render(request, "travellers/user_profile.html", context)

# ==================== RESTAURANT DETAIL ====================
def restaurant_detail(request, pk):
    """
    View restaurant/hotel details with booking options
    """

    restaurant = get_object_or_404(
        RestaurantProfile,
        id=pk,
        is_approved=True
    )

    # =====================================
    # MEDIA
    # =====================================

    media_images = restaurant.media.all()

    media_by_section = {}

    for media in media_images:
        media_by_section.setdefault(
            media.section,
            []
        ).append(media)

    # =====================================
    # WISHLIST
    # =====================================

    is_wishlisted = False

    if request.user.is_authenticated:
        is_wishlisted = Wishlist.objects.filter(
            user=request.user,
            restaurant=restaurant
        ).exists()

    # =====================================
    # TABLES
    # =====================================

    tables = None
    available_tables = None

    if restaurant.has_table_service:

        tables = restaurant.tables.filter(
            is_active=True,
            is_reservable=True
        )

        booking_date = request.GET.get("date")

        if booking_date:

            from datetime import datetime

            try:

                date_obj = datetime.strptime(
                    booking_date,
                    "%Y-%m-%d"
                ).date()

                booked_table_ids = TableBooking.objects.filter(
                    table__restaurant=restaurant,
                    start_time__date=date_obj,
                    status__in=[
                        "pending",
                        "confirmed"
                    ]
                ).values_list(
                    "table_id",
                    flat=True
                )

                available_tables = tables.exclude(
                    id__in=booked_table_ids
                )

            except Exception:
                available_tables = tables

        else:
            available_tables = tables

    # =====================================
    # ROOM TYPES
    # =====================================

    room_types = None

    if restaurant.has_room_service:

        room_types = restaurant.room_types.prefetch_related(
            "rooms",
            "detail",
            "images"
        )

        check_in = request.GET.get("check_in")
        check_out = request.GET.get("check_out")

        if check_in and check_out:

            from datetime import datetime

            try:

                check_in_date = datetime.strptime(
                    check_in,
                    "%Y-%m-%d"
                ).date()

                check_out_date = datetime.strptime(
                    check_out,
                    "%Y-%m-%d"
                ).date()

                for room_type in room_types:

                    booked_room_ids = RoomBooking.objects.filter(
                        room__room_type=room_type,
                        check_in__lt=check_out_date,
                        check_out__gt=check_in_date,
                        status="confirmed"
                    ).values_list(
                        "room_id",
                        flat=True
                    )

                    total_rooms = room_type.rooms.filter(
                        status="available"
                    ).count()

                    booked_rooms = room_type.rooms.filter(
                        id__in=booked_room_ids
                    ).count()

                    room_type.available_rooms = (
                        total_rooms - booked_rooms
                    )

            except Exception:

                for room_type in room_types:
                    room_type.available_rooms = room_type.rooms.filter(
                        status="available"
                    ).count()

        else:

            for room_type in room_types:
                room_type.available_rooms = room_type.rooms.filter(
                    status="available"
                ).count()

    # =====================================
    # RATINGS
    # =====================================

    ratings = {
        "average": restaurant.avg_rating,
        "count": restaurant.total_reviews,
    }

    # =====================================
    # CONTEXT
    # =====================================

    context = {
        "restaurant": restaurant,
        "media_images": media_images,
        "media_by_section": media_by_section,

        "tables": tables,
        "available_tables": available_tables,

        "room_types": room_types,

        "ratings": ratings,

        "is_wishlisted": is_wishlisted,
    }

    return render(
        request,
        "travellers/restaurant_detail.html",
        context
    )


@login_required
def book_table(request, pk):

    property_obj = get_object_or_404(RestaurantProfile, id=pk, is_approved=True)

    available_tables = property_obj.tables.filter(
        is_active=True,
        is_reservable=True
    )

    if request.method == "POST":

        guests = int(request.POST.get("guests", 1))
        adults = int(request.POST.get("adults", 1))
        children = int(request.POST.get("children", 0))
        special_request = request.POST.get("special_request", "")

        table_id = request.POST.get("table_id")
        start_time = request.POST.get("start_time")
        end_time = request.POST.get("end_time")

        if not all([table_id, start_time, end_time]):
            messages.error(request, "Please select table and time slot.")
            return redirect("travellers:book_table", pk=pk)

        table = get_object_or_404(Table, id=table_id, restaurant=property_obj)

        if guests > table.capacity:
            messages.error(request, f"Max capacity is {table.capacity}")
            return redirect("travellers:book_table", pk=pk)

        conflict = TableBooking.objects.filter(
            table=table,
            status__in=["pending", "confirmed"],
            start_time__lt=end_time,
            end_time__gt=start_time
        ).exists()

        if conflict:
            messages.error(request, "Slot already booked.")
            return redirect("travellers:book_table", pk=pk)

        booking = TableBooking.objects.create(
            table=table,
            user=request.user,
            start_time=start_time,
            end_time=end_time,
            guests=guests,
            status="pending"
        )

        if property_obj.requires_table_advance:
            return redirect("travellers:table_booking_payment", booking_id=booking.id)

        booking.status = "confirmed"
        booking.save()

        messages.success(request, "Table booked successfully.")
        return redirect("travellers:my_bookings")

    return render(request, "travellers/book_table.html", {
        "property": property_obj,
        "available_tables": available_tables,
        "booking_type": "table"
    })


@login_required
def book_room(request, pk):
    """Separate view for room booking"""

    property_obj = get_object_or_404(
        RestaurantProfile,
        id=pk,
        is_approved=True
    )

    # Get available room types
    available_rooms = RoomType.objects.filter(
        restaurant=property_obj
    ).prefetch_related(
        "rooms",
        "cancellation_policy",
    )

    # Add availability count
    for room_type in available_rooms:
        room_type.available_rooms = room_type.rooms.filter(
            status="available"
        ).count()

    if request.method == "POST":

        guests = int(request.POST.get("guests", 1))
        adults = int(request.POST.get("adults", 1))
        children = int(request.POST.get("children", 0))
        special_request = request.POST.get("special_request", "")

        room_type_id = request.POST.get("room_type_id")
        check_in = request.POST.get("check_in")
        check_out = request.POST.get("check_out")

        # -----------------------------
        # VALIDATION
        # -----------------------------
        if not all([room_type_id, check_in, check_out]):
            messages.error(request, "Please select room type and dates.")
            return redirect("travellers:book_room", pk=pk)

        try:
            check_in_date = datetime.strptime(check_in, "%Y-%m-%d").date()
            check_out_date = datetime.strptime(check_out, "%Y-%m-%d").date()
        except ValueError:
            messages.error(request, "Invalid date format.")
            return redirect("travellers:book_room", pk=pk)

        if check_out_date <= check_in_date:
            messages.error(request, "Check-out must be after check-in.")
            return redirect("travellers:book_room", pk=pk)

        # -----------------------------
        # ROOM TYPE CHECK
        # -----------------------------
        room_type = get_object_or_404(
            RoomType,
            id=room_type_id,
            restaurant=property_obj
        )

        if guests > room_type.max_guests:
            messages.error(
                request,
                f"Maximum {room_type.max_guests} guests allowed."
            )
            return redirect("travellers:book_room", pk=pk)

        # -----------------------------
        # FIND AVAILABLE ROOM
        # -----------------------------
        booked_room_ids = RoomBooking.objects.filter(
            room__room_type=room_type,
            status__in=["pending", "confirmed"],
            check_in__lt=check_out_date,
            check_out__gt=check_in_date
        ).values_list("room_id", flat=True)

        available_room = Room.objects.filter(
            room_type=room_type,
            status="available"
        ).exclude(
            id__in=booked_room_ids
        ).first()

        if not available_room:
            messages.error(
                request,
                f"No {room_type.name} rooms available for selected dates."
            )
            return redirect("travellers:book_room", pk=pk)

        # -----------------------------
        # PRICE CALCULATION
        # -----------------------------
        nights = (check_out_date - check_in_date).days
        total_amount = room_type.price_per_night * nights

        # -----------------------------
        # CREATE BOOKING
        # -----------------------------
        room_booking = RoomBooking.objects.create(
            room=available_room,
            user=request.user,
            check_in=check_in_date,
            check_out=check_out_date,
            nights=nights,
            guests=guests,
            adults=adults,
            children=children,
            price_per_night=room_type.price_per_night,
            total_amount=total_amount,
            special_request=special_request,
            status="pending"
        )

        # -----------------------------
        # PAYMENT FLOW
        # -----------------------------
        return redirect(
            "travellers:room_booking_payment",
            booking_id=room_booking.id
        )

    return render(
        request,
        "travellers/book_room.html",
        {
            "property": property_obj,
            "available_rooms": available_rooms,
            "booking_type": "room",
        }
    )


@login_required
def room_payment_success(request, booking_id):

    booking = get_object_or_404(
        RoomBooking,
        id=booking_id,
        user=request.user
    )

    data = json.loads(request.body)

    try:

        client.utility.verify_payment_signature({
            "razorpay_order_id": data["razorpay_order_id"],
            "razorpay_payment_id": data["razorpay_payment_id"],
            "razorpay_signature": data["razorpay_signature"]
        })

        RestaurantPayment.objects.create(
            user=request.user,
            room_booking=booking,
            payment_type="room",
            amount=booking.total_amount,
            transaction_id=data["razorpay_payment_id"],
            status="success"
        )

        booking.status = "confirmed"
        booking.payment_status = "paid"
        booking.save()

        create_audit_log(
            request.user,
            "ROOM_PAYMENT_SUCCESS",
            f"Room payment successful for booking #{booking.id} at {booking.room.room_type.restaurant.restaurant_name}. Amount: ₹{booking.total_amount}"
        )

        return JsonResponse({
            "status": "success",
            "booking_id": booking.id,
            "payment_type": "Room Booking",
            "amount": str(booking.total_amount)
        })

    except Exception as e:

        return JsonResponse({
            "status": "failed",
            "error": str(e)
        }, status=400)

@login_required
def table_payment_success(request, booking_id):

    booking = get_object_or_404(
        TableBooking,
        id=booking_id,
        user=request.user
    )

    try:

        print("METHOD:", request.method)
        print("BODY:", request.body)

        data = json.loads(request.body)

        print("DATA:", data)

        client.utility.verify_payment_signature({
            "razorpay_order_id": data["razorpay_order_id"],
            "razorpay_payment_id": data["razorpay_payment_id"],
            "razorpay_signature": data["razorpay_signature"]
        })

        booking.status = "confirmed"
        booking.save()

        create_audit_log(
            request.user,
            "TABLE_PAYMENT_SUCCESS",
            f"Table payment successful for booking #{booking.id} at {booking.table.restaurant.restaurant_name}. Amount: ₹{booking.table.restaurant.table_advance_amount}"
        )

        RestaurantPayment.objects.create(
            user=request.user,
            table_booking=booking,
            payment_type="table",
            amount=booking.table.restaurant.table_advance_amount,
            transaction_id=data["razorpay_payment_id"],
            status="success"
        )

        Notification.objects.create(
            user=request.user,
            notification_type="payment",
            message=f"Table booking confirmed at {booking.table.restaurant.restaurant_name} 🍽️"
        )

        return JsonResponse({
            "status": "success",
            "booking_id": booking.id,
            "amount": str(
                booking.table.restaurant.table_advance_amount
            ),
            "payment_type": "Table Reservation"
        })

    except Exception as e:

        import traceback

        print("=" * 80)
        print("TABLE PAYMENT ERROR")
        print(str(e))
        print(traceback.format_exc())
        print("=" * 80)

        return JsonResponse({
            "status": "failed",
            "error": str(e)
        }, status=400)

@login_required
def room_booking_payment(request, booking_id):

    booking = get_object_or_404(
        RoomBooking,
        id=booking_id,
        user=request.user
    )

    amount_paise = int(booking.total_amount * 100)

    razorpay_order = client.order.create({
        "amount": amount_paise,
        "currency": "INR",
        "payment_capture": 1
    })

    return render(
        request,
        "payments/room_payment.html",
        {
            "booking": booking,
            "amount": booking.total_amount,     # display
            "amount_paise": amount_paise,       # Razorpay
            "razorpay_key": settings.RAZORPAY_KEY_ID,
            "razorpay_order_id": razorpay_order["id"],
        }
    )

@login_required
def table_booking_payment(request, booking_id):

    booking = get_object_or_404(
        TableBooking,
        id=booking_id,
        user=request.user
    )

    table_amount = booking.table.restaurant.table_advance_amount

    razorpay_amount = int(table_amount * 100)

    razorpay_order = client.order.create({
        "amount": razorpay_amount,
        "currency": "INR",
        "payment_capture": 1
    })

    return render(
        request,
        "payments/table_payment.html",
        {
            "booking": booking,
            "display_amount": table_amount,   # ₹100
            "amount": razorpay_amount,        # 10000 paise
            "razorpay_key": settings.RAZORPAY_KEY_ID,
            "razorpay_order_id": razorpay_order["id"],
        }
    )

# ==================== EDIT PROFILE ====================
@login_required
def edit_profile(request):
    """Edit traveller profile with cover image"""
    profile = get_object_or_404(TravellerProfile, user=request.user)
    
    if request.method == "POST":
        form = TravellerProfileEditForm(request.POST, request.FILES, instance=profile, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            create_audit_log(
                request.user,
                "UPDATE_PROFILE",
                "Updated traveller profile information"
            )
            return redirect("travellers:user_profile", user_id=request.user.id)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = TravellerProfileEditForm(instance=profile, user=request.user)
    
    return render(request, "travellers/edit_profile.html", {
        "form": form,
        "profile": profile
    })

# ==================== BOOKINGS ====================
@login_required
def my_bookings(request):
    """Display user's bookings - packages, rooms, and tables"""
    
    from datetime import timedelta
    from django.utils import timezone
    
    # Auto-cancel expired bookings
    expiry_time = timezone.now() - timedelta(hours=24)
    
    # Cancel expired package bookings
    PackageBooking.objects.filter(
        status='pending',
        booked_at__lt=expiry_time
    ).update(status='cancelled')
    
    # Cancel expired room bookings
    RoomBooking.objects.filter(
        status='pending',
        created_at__lt=expiry_time
    ).update(status='cancelled')
    
    # Cancel expired table bookings (if start_time has passed)
    TableBooking.objects.filter(
        status='pending',
        start_time__lt=timezone.now()
    ).update(status='cancelled')
    
    # Get all bookings
    package_bookings = PackageBooking.objects.filter(
        traveller=request.user
    ).select_related('package', 'package__agency').order_by("-booked_at")
    
    room_bookings = RoomBooking.objects.filter(
        user=request.user
    ).select_related(
        "room",
        "room__room_type",
        "room__room_type__restaurant"
    ).order_by("-created_at")
    
    table_bookings = TableBooking.objects.filter(
        user=request.user
    ).select_related(
        "table",
        "table__restaurant"
    ).order_by("-start_time")
    
    # Create lists with calculated properties instead of modifying model instances
    package_list = []
    for booking in package_bookings:
        # Calculate payment progress
        payment_progress = 0
        remaining_amount = 0
        if booking.total_amount:
            paid = 0
            if booking.payment_status == 'partial':
                paid = float(booking.advance_amount) if booking.advance_amount else 0
            elif booking.payment_status == 'paid':
                paid = float(booking.total_amount)
            
            payment_progress = int((paid / float(booking.total_amount)) * 100) if booking.total_amount else 0
            remaining_amount = float(booking.total_amount) - paid
        
        package_list.append({
            'id': booking.id,
            'package': booking.package,
            'travellers_count': booking.travellers_count,
            'travel_date': booking.travel_date,
            'total_amount': booking.total_amount,
            'advance_amount': booking.advance_amount,
            'status': booking.status,
            'payment_status': booking.payment_status,
            'booked_at': booking.booked_at,
            'payment_progress': payment_progress,
            'remaining_amount': remaining_amount,
            'can_review': booking.status == 'completed',
            'review': None,
        })
    
    # Combine property bookings for the template
    property_bookings = []
    
    # Add room bookings to property_bookings
    for booking in room_bookings:
        property_bookings.append({
            'id': booking.id,
            'booking_type': 'room',
            'property': booking.room.room_type.restaurant,
            'status': booking.status,
            'check_in': booking.check_in,
            'check_out': booking.check_out,
            'guests': booking.guests,
            'rooms': 1,
            'total_amount': float(booking.total_amount) if booking.total_amount else 0,
            'advance_paid': float(booking.total_amount) if booking.status == 'confirmed' else 0,
            'booking_date': booking.created_at.date() if booking.created_at else None,
            'time': None,
        })
    
    # Add table bookings to property_bookings
    for booking in table_bookings:
        property_bookings.append({
            'id': booking.id,
            'booking_type': 'table',
            'property': booking.table.restaurant,
            'status': booking.status,
            'booking_date': booking.start_time.date() if booking.start_time else None,
            'time': booking.start_time.strftime('%I:%M %p') if booking.start_time else None,
            'guests': booking.guests,
            'total_amount': float(booking.table.restaurant.table_advance_amount) if booking.table.restaurant.requires_table_advance else 0,
            'advance_paid': float(booking.advance_paid) if booking.advance_paid else 0,
            'check_in': None,
            'check_out': None,
            'rooms': None,
        })
    
    # Calculate counts for stats
    confirmed_count = 0
    pending_count = 0
    completed_count = 0
    cancelled_count = 0
    
    # Count package bookings
    for booking in package_bookings:
        if booking.status == 'confirmed':
            confirmed_count += 1
        elif booking.status == 'pending':
            pending_count += 1
        elif booking.status == 'completed':
            completed_count += 1
        elif booking.status == 'cancelled':
            cancelled_count += 1
    
    # Count room bookings
    for booking in room_bookings:
        if booking.status == 'confirmed':
            confirmed_count += 1
        elif booking.status == 'pending':
            pending_count += 1
        elif booking.status == 'completed':
            completed_count += 1
        elif booking.status == 'cancelled':
            cancelled_count += 1
    
    # Count table bookings
    for booking in table_bookings:
        if booking.status == 'confirmed':
            confirmed_count += 1
        elif booking.status == 'pending':
            pending_count += 1
        elif booking.status == 'completed':
            completed_count += 1
        elif booking.status == 'cancelled':
            cancelled_count += 1
    
    context = {
        'package_bookings': package_list,  # Use the list with calculated properties
        'property_bookings': property_bookings,
        'room_bookings': room_bookings,
        'table_bookings': table_bookings,
        'confirmed_count': confirmed_count,
        'pending_count': pending_count,
        'completed_count': completed_count,
        'cancelled_count': cancelled_count,
    }
    
    return render(request, "travellers/my_bookings.html", context)

def auto_cancel_expired_bookings():
    """Auto-cancel pending bookings older than 24 hours"""
    from datetime import timedelta
    from django.utils import timezone
    
    expiry_time = timezone.now() - timedelta(hours=24)
    
    # Cancel expired package bookings
    PackageBooking.objects.filter(
        status='pending',
        booked_at__lt=expiry_time
    ).update(status='cancelled')
    
    # Cancel expired room bookings
    RoomBooking.objects.filter(
        status='pending',
        created_at__lt=expiry_time
    ).update(status='cancelled')
    
    # Cancel expired table bookings - TableBooking doesn't have created_at
    # Use a different field or just skip auto-cancel for tables
    # TableBooking has start_time, so we can use that
    TableBooking.objects.filter(
        status='pending',
        start_time__lt=timezone.now()  # Cancel if start time has passed
    ).update(status='cancelled')


# ==================== ALL RESTAURANTS ====================
# travellers/views.py - Updated all_restaurants view

from django.shortcuts import render
from django.core.paginator import Paginator
from django.db.models import Q
from restaurants.models import RestaurantProfile  # Correct model name
from django.db.models import Avg, Count, Q


def all_restaurants(request):
    # Use RestaurantProfile instead of Restaurant
    qs = RestaurantProfile.objects.filter(is_approved=True)

    # ── Query params ──────────────────────────────────────────────────
    search_query = request.GET.get('search', '').strip()
    property_type = request.GET.get('property_type', '').strip()
    service_type = request.GET.get('service_type', '').strip()
    city = request.GET.get('city', '').strip()
    has_ac = request.GET.get('has_ac', '').strip()
    outdoor = request.GET.get('outdoor', '').strip()
    min_price = request.GET.get('min_price', '').strip()
    max_price = request.GET.get('max_price', '').strip()
    sort_by = request.GET.get('sort', 'name').strip()

    # ── Base filters ──────────────────────────────────────────────────
    if search_query:
        qs = qs.filter(
            Q(restaurant_name__icontains=search_query) |
            Q(city__icontains=search_query) |
            Q(cuisine_tags__icontains=search_query) |
            Q(state__icontains=search_query)
        )

    if property_type:
        qs = qs.filter(property_type=property_type)

    if city:
        qs = qs.filter(city__iexact=city)

    if service_type == 'dining':
        qs = qs.filter(has_table_service=True)
    elif service_type == 'accommodation':
        qs = qs.filter(has_room_service=True)

    # Dining features
    if has_ac == 'yes':
        qs = qs.filter(tables__has_ac=True).distinct()
    if outdoor == 'yes':
        qs = qs.filter(tables__zone__icontains='outdoor').distinct()

    # Price range filter for rooms
    if min_price or max_price:
        if min_price and max_price:
            qs = qs.filter(
                room_types__price_per_night__gte=min_price,
                room_types__price_per_night__lte=max_price
            ).distinct()
        elif min_price:
            qs = qs.filter(room_types__price_per_night__gte=min_price).distinct()
        elif max_price:
            qs = qs.filter(room_types__price_per_night__lte=max_price).distinct()

    # ── Sort ──────────────────────────────────────────────────────────
    sort_map = {
        'name': 'restaurant_name',
        'rating': '-avg_rating',
        'newest': '-created_at',
        'price_low': 'room_types__price_per_night',
        'price_high': '-room_types__price_per_night',
    }
    qs = qs.distinct().order_by(sort_map.get(sort_by, 'restaurant_name'))

    # ── Counts for tab badges ─────────────────────────────────────────
    base = RestaurantProfile.objects.filter(is_approved=True)
    
    if search_query:
        base = base.filter(
            Q(restaurant_name__icontains=search_query) |
            Q(city__icontains=search_query) |
            Q(cuisine_tags__icontains=search_query)
        )

    property_counts = {
        'total': base.count(),
        'restaurants': base.filter(property_type='Restaurant').count(),
        'cafe': base.filter(property_type='Cafe').count(),
        'hotel': base.filter(property_type='Hotel').count(),
        'resort': base.filter(property_type='Resort').count(),
        'homestay': base.filter(property_type='Homestay').count(),
    }

    # ── Cities dropdown ───────────────────────────────────────────────
    cities = base.values_list('city', flat=True).order_by('city').distinct()

    # ── Grouped lists for "All" view ────────────────────────────────────
    restaurants_list = []
    cafes_list = []
    hotels_list = []
    resorts_list = []
    homestays_list = []
    
    if not property_type:
        restaurants_list = list(base.filter(property_type='Restaurant')[:6])
        cafes_list = list(base.filter(property_type='Cafe')[:6])
        hotels_list = list(base.filter(property_type='Hotel')[:6])
        resorts_list = list(base.filter(property_type='Resort')[:6])
        homestays_list = list(base.filter(property_type='Homestay')[:6])

    # ── Paginator for filtered single-type view ────────────────────────
    paginator = Paginator(qs, 12)
    page_number = request.GET.get('page', 1)
    restaurants = paginator.get_page(page_number)

    # ── Get wishlist IDs for the current user ─────────────────────────
    wishlisted_ids = set(
    Wishlist.objects.filter(
        user=request.user,
        restaurant__isnull=False
    ).values_list('restaurant_id', flat=True)
)

    return render(request, 'travellers/all_restaurants.html', {
        'restaurants': restaurants,
        'restaurants_list': restaurants_list,
        'cafes_list': cafes_list,
        'hotels_list': hotels_list,
        'resorts_list': resorts_list,
        'homestays_list': homestays_list,
        'property_counts': property_counts,
        'cities': cities,
        'search_query': search_query,
        'property_type': property_type,
        'service_type': service_type,
        'has_ac': has_ac,
        'outdoor': outdoor,
        'min_price': min_price,
        'max_price': max_price,
        'sort_by': sort_by,
        'wishlisted_ids': wishlisted_ids,  # Pass wishlist IDs to template
    })

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
    page_number = request.GET.get('page', 1)
    packages_page = paginator.get_page(page_number)
    
    # ========== GET WISHLIST IDs FOR CURRENT USER ==========
    wishlisted_ids = []
    if request.user.is_authenticated:
        wishlisted_ids = Wishlist.objects.filter(
            user=request.user,
            package__isnull=False
        ).values_list('package_id', flat=True)
        wishlisted_ids = list(wishlisted_ids)
    
    # Get unread notifications count
    unread_notifications = Notification.objects.filter(user=request.user, is_read=False).count()
    
    context = {
        'profile': profile,
        'packages': packages_page,
        'unread_notifications': unread_notifications,
        'current_category': category,
        'current_sort': sort_by,
        'wishlisted_ids': wishlisted_ids,  # Add wishlist IDs to context
    }
    
    return render(request, 'travellers/all_packages.html', context)


# ==================== PACKAGE DETAIL ====================
def package_detail(request, id):
    package = get_object_or_404(TourPackage, id=id, is_active=True)
    
    itineraries = package.itineraries.all().order_by('day_number')
    images = package.images.all()
    
    # Check wishlist
    is_wishlisted = Wishlist.objects.filter(user=request.user, package=package).exists() if request.user.is_authenticated else False
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

            existing_booking = PackageBooking.objects.filter(
                traveller=request.user,
                travel_date=travel_date,
                status__in=["pending", "confirmed"]
            ).exists()

            if existing_booking:
                messages.error(
                    request,
                    "You already have another package booked on this date."
                )
                return redirect('travellers:book_package', id=package.id)
            
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
                payment_status="pending",
                approval_deadline=timezone.now() + timedelta(hours=24)
            )

            create_audit_log(
                request.user,
                "BOOK_PACKAGE",
                f"Booked package '{package.title}' for {travellers_count} traveller(s) on {travel_date}"
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
def cancel_booking(request, booking_type, booking_id):
    """
    Unified cancel booking view for all booking types
    booking_type can be: 'package', 'room', 'table'
    """
    try:
        if booking_type == 'package':
            booking = get_object_or_404(PackageBooking, id=booking_id, traveller=request.user)
            
            if booking.status not in ["pending", "confirmed"]:
                return JsonResponse({'success': False, 'error': 'This booking cannot be cancelled'}, status=400)
            
            # Calculate refund for package
            refund_amount = booking.calculate_refund_amount()
            refund_percentage = booking.get_refund_percentage()
            
            # Update booking
            booking.status = "cancelled"
            booking.cancelled_by = "user"
            booking.save()

            create_audit_log(
                request.user,
                "CANCEL_BOOKING",
                f"Cancelled package booking #{booking.id} for package '{booking.package.title}'"
            )
                        
            # Notify agency
            Notification.objects.create(
                user=booking.package.agency.user,
                notification_type="booking",
                message=(
                    f"Booking cancelled by {request.user.get_full_name() or request.user.username} "
                    f"for {booking.package.title}. Refund: ₹{refund_amount:,.2f} ({refund_percentage}%)"
                )
            )
            
            message = f"Booking cancelled successfully. Refund: ₹{refund_amount:,.2f} ({refund_percentage}%)"
            
        elif booking_type == 'room':
            booking = get_object_or_404(RoomBooking, id=booking_id, user=request.user)
            
            if booking.status not in ["pending", "confirmed"]:
                return JsonResponse({'success': False, 'error': 'This booking cannot be cancelled'}, status=400)
            
            # Calculate refund for room booking based on cancellation policy
            refund_amount = 0
            refund_percentage = 0
            
            room_type = booking.room.room_type
            if hasattr(room_type, 'cancellation_policy'):
                policy = room_type.cancellation_policy
                from datetime import date
                days_until_checkin = (booking.check_in - date.today()).days
                
                if policy.policy_type == 'free':
                    refund_percentage = 100
                    refund_amount = float(booking.total_amount)
                elif days_until_checkin > policy.free_until_days:
                    refund_percentage = 100
                    refund_amount = float(booking.total_amount)
                elif days_until_checkin >= 0:
                    refund_percentage = policy.refund_percentage_after
                    refund_amount = float(booking.total_amount) * refund_percentage / 100
                else:
                    refund_percentage = 0
                    refund_amount = 0
            else:
                # Default: 100% refund if cancelled within 24 hours of booking
                from django.utils import timezone
                from datetime import timedelta
                if booking.created_at > timezone.now() - timedelta(hours=24):
                    refund_percentage = 100
                    refund_amount = float(booking.total_amount)
                else:
                    refund_percentage = 0
                    refund_amount = 0
            
            # Update booking
            booking.status = "cancelled"
            booking.save()

            create_audit_log(
                request.user,
                "CANCEL_BOOKING",
                f"Cancelled room booking #{booking.id} at {booking.room.room_type.restaurant.restaurant_name}"
            )
            
            # Notify restaurant
            Notification.objects.create(
                user=booking.room.room_type.restaurant.user,
                notification_type="booking",
                message=(
                    f"Room booking cancelled by {request.user.get_full_name() or request.user.username} "
                    f"for {booking.room.room_type.name} at {booking.room.room_type.restaurant.restaurant_name}"
                )
            )
            
            message = f"Room booking cancelled successfully. Refund: ₹{refund_amount:,.2f} ({refund_percentage}%)"
            
        elif booking_type == 'table':
            booking = get_object_or_404(TableBooking, id=booking_id, user=request.user)
            
            if booking.status not in ["pending", "confirmed"]:
                return JsonResponse({'success': False, 'error': 'This booking cannot be cancelled'}, status=400)
            
            # Table booking: NO REFUND (advance payment is non-refundable)
            refund_amount = 0
            refund_percentage = 0
            
            # Update booking
            booking.status = "cancelled"
            booking.save()
            
            create_audit_log(
                request.user,
                "CANCEL_BOOKING",
                f"Cancelled table booking #{booking.id} at {booking.table.restaurant.restaurant_name}"
            )
            
            # Notify restaurant
            Notification.objects.create(
                user=booking.table.restaurant.user,
                notification_type="booking",
                message=(
                    f"Table booking cancelled by {request.user.get_full_name() or request.user.username} "
                    f"for Table {booking.table.table_number} at {booking.table.restaurant.restaurant_name}"
                )
            )
            
            message = "Table booking cancelled successfully. Note: Advance payment is non-refundable."
            
        else:
            return JsonResponse({'success': False, 'error': 'Invalid booking type'}, status=400)
        
        # For AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': message,
                'refund_amount': refund_amount,
                'refund_percentage': refund_percentage
            })
        
        # For regular form submissions
        messages.success(request, message)
        return redirect("travellers:my_bookings")
        
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
        messages.error(request, f'Error cancelling booking: {str(e)}')
        return redirect("travellers:my_bookings")


# ==================== WISHLIST ====================
@login_required
def wishlist(request):
    """Display user's wishlist with both packages and restaurants"""
    
    wishlist_items = Wishlist.objects.filter(user=request.user).select_related('package', 'package__agency', 'restaurant')
    
    # Separate items by type
    packages = []
    restaurants = []
    
    for item in wishlist_items:
        if item.package:
            packages.append(item.package)
        elif item.restaurant:
            restaurants.append(item.restaurant)
    
    context = {
        'packages': packages,
        'restaurants': restaurants,
        'total_items': len(packages) + len(restaurants),
    }
    
    return render(request, "travellers/wishlist.html", context)


@login_required
def wishlist_add(request, item_id, item_type='package'):
    """Add/remove item from wishlist (supports both packages and restaurants)"""
    
    if request.method == 'POST':
        try:
            if item_type == 'package':
                item = get_object_or_404(TourPackage, id=item_id, is_active=True)
                wishlist_item = Wishlist.objects.filter(user=request.user, package=item)
                
                if wishlist_item.exists():
                    wishlist_item.delete()
                    status = 'removed'
                    message = 'Removed from wishlist'
                else:
                    Wishlist.objects.create(user=request.user, package=item)
                    status = 'added'
                    message = 'Added to wishlist'
                    
            elif item_type == 'restaurant':
                item = get_object_or_404(RestaurantProfile, id=item_id, is_approved=True)
                wishlist_item = Wishlist.objects.filter(user=request.user, restaurant=item)
                
                if wishlist_item.exists():
                    wishlist_item.delete()
                    status = 'removed'
                    message = 'Removed from wishlist'
                else:
                    Wishlist.objects.create(user=request.user, restaurant=item)
                    status = 'added'
                    message = 'Added to wishlist'
            else:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'error': 'Invalid item type'}, status=400)
                messages.error(request, 'Invalid item type')
                return redirect(request.META.get('HTTP_REFERER', 'travellers:dashboard'))
            
            # Get updated count
            wishlist_count = Wishlist.objects.filter(user=request.user).count()
            
            # Return JSON response for AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': status,
                    'message': message,
                    'count': wishlist_count,
                    'item_id': item_id,
                    'item_type': item_type
                })
            
            # For regular form submissions
            messages.success(request, message)
            return redirect(request.META.get('HTTP_REFERER', 'travellers:dashboard'))
            
        except Exception as e:
            print(f"Error in wishlist_add: {e}")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'error': str(e)}, status=400)
            messages.error(request, f'Error: {str(e)}')
            return redirect(request.META.get('HTTP_REFERER', 'travellers:dashboard'))
    
    return JsonResponse({'error': 'Invalid request method'}, status=400)


@login_required
def wishlist_remove(request, item_id, item_type='package'):
    """Remove item from wishlist"""
    
    if request.method == 'POST':
        try:
            if item_type == 'package':
                wishlist_item = Wishlist.objects.filter(user=request.user, package_id=item_id).first()
                item_name = wishlist_item.package.title if wishlist_item else 'Item'
            elif item_type == 'restaurant':
                wishlist_item = Wishlist.objects.filter(user=request.user, restaurant_id=item_id).first()
                item_name = wishlist_item.restaurant.restaurant_name if wishlist_item else 'Item'
            else:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'error': 'Invalid item type'}, status=400)
                messages.error(request, 'Invalid item type')
                return redirect("travellers:wishlist")
            
            if wishlist_item:
                wishlist_item.delete()
                message = f"{item_name} removed from wishlist"
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'status': 'removed',
                        'message': message,
                        'item_id': item_id,
                        'item_type': item_type
                    })
                
                messages.success(request, message)
            else:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'error': 'Item not found in wishlist'}, status=404)
                messages.warning(request, "Item not found in wishlist.")
                
        except Exception as e:
            print(f"Error in wishlist_remove: {e}")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'error': str(e)}, status=400)
            messages.error(request, f'Error: {str(e)}')
    
    return redirect("travellers:wishlist")


@login_required
def wishlist_add_restaurant(request, pk):
    """Add restaurant to wishlist via AJAX (simplified version)"""
    if request.method == 'POST':
        try:
            restaurant = get_object_or_404(RestaurantProfile, id=pk, is_approved=True)
            wishlist_item = Wishlist.objects.filter(user=request.user, restaurant=restaurant)
            
            if wishlist_item.exists():
                wishlist_item.delete()
                status = 'removed'
                message = 'Removed from wishlist'
            else:
                Wishlist.objects.create(user=request.user, restaurant=restaurant)
                status = 'added'
                message = 'Added to wishlist'
            
            # Get updated count
            wishlist_count = Wishlist.objects.filter(user=request.user).count()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': status,
                    'message': message,
                    'count': wishlist_count,
                    'restaurant_id': restaurant.id,
                    'restaurant_name': restaurant.restaurant_name
                })
            
            messages.success(request, message)
            return redirect(request.META.get('HTTP_REFERER', 'travellers:restaurant_detail', pk=pk))
            
        except Exception as e:
            print(f"Error in wishlist_add_restaurant: {e}")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'error': str(e)}, status=400)
            messages.error(request, f'Error: {str(e)}')
            return redirect(request.META.get('HTTP_REFERER', 'travellers:dashboard'))
    
    return JsonResponse({'error': 'Invalid request'}, status=400)


@login_required
def wishlist_remove_restaurant(request, pk):
    """Remove restaurant from wishlist"""
    if request.method == 'POST':
        try:
            restaurant = get_object_or_404(RestaurantProfile, id=pk)
            wishlist_item = Wishlist.objects.filter(user=request.user, restaurant=restaurant)
            
            if wishlist_item.exists():
                wishlist_item.delete()
                message = f"{restaurant.restaurant_name} removed from wishlist"
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'status': 'removed',
                        'message': message,
                        'restaurant_id': restaurant.id
                    })
                
                messages.success(request, message)
            else:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'error': 'Item not found in wishlist'}, status=404)
                messages.warning(request, "Item not found in wishlist.")
                
        except Exception as e:
            print(f"Error in wishlist_remove_restaurant: {e}")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'error': str(e)}, status=400)
            messages.error(request, f'Error: {str(e)}')
    
    return redirect('travellers:wishlist')


@login_required
def wishlist_add_package(request, pk):
    """Add package to wishlist via AJAX"""
    if request.method == 'POST':
        try:
            package = get_object_or_404(TourPackage, id=pk, is_active=True)
            wishlist_item = Wishlist.objects.filter(user=request.user, package=package)
            
            if wishlist_item.exists():
                wishlist_item.delete()
                status = 'removed'
                message = 'Removed from wishlist'
            else:
                Wishlist.objects.create(user=request.user, package=package)
                status = 'added'
                message = 'Added to wishlist'
            
            # Get updated count
            wishlist_count = Wishlist.objects.filter(user=request.user).count()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': status,
                    'message': message,
                    'count': wishlist_count,
                    'package_id': package.id,
                    'package_title': package.title
                })
            
            messages.success(request, message)
            return redirect(request.META.get('HTTP_REFERER', 'travellers:package_detail', pk=pk))
            
        except Exception as e:
            print(f"Error in wishlist_add_package: {e}")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'error': str(e)}, status=400)
            messages.error(request, f'Error: {str(e)}')
            return redirect(request.META.get('HTTP_REFERER', 'travellers:dashboard'))
    
    return JsonResponse({'error': 'Invalid request'}, status=400)


@login_required
def wishlist_remove_package(request, pk):
    """Remove package from wishlist"""
    if request.method == 'POST':
        try:
            package = get_object_or_404(TourPackage, id=pk)
            wishlist_item = Wishlist.objects.filter(user=request.user, package=package)
            
            if wishlist_item.exists():
                wishlist_item.delete()
                message = f"{package.title} removed from wishlist"
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'status': 'removed',
                        'message': message,
                        'package_id': package.id
                    })
                
                messages.success(request, message)
            else:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'error': 'Item not found in wishlist'}, status=404)
                messages.warning(request, "Item not found in wishlist.")
                
        except Exception as e:
            print(f"Error in wishlist_remove_package: {e}")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'error': str(e)}, status=400)
            messages.error(request, f'Error: {str(e)}')
    
    return redirect('travellers:wishlist')



# ==================== CHANGE PASSWORD ====================
@login_required
def change_password(request):
    if request.method == "POST":
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)

            create_audit_log(
                user=request.user,
                action='password_changed',
                description='Changed account password'
            )

            messages.success(request, "✓ Password updated successfully! Please use your new password next time you log in.")
            return redirect('travellers:dashboard')
        else:
            # Collect all errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"❌ {error}")
    else:
        form = PasswordChangeForm(user=request.user)
    
    return render(request, 'travellers/change_password.html', {'form': form})


from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.models import User
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

@login_required
def change_email(request):
    """View for users to change their email address"""
    
    if request.method == 'POST':
        new_email = request.POST.get('new_email', '').strip()
        confirm_email = request.POST.get('confirm_email', '').strip()
        current_password = request.POST.get('current_password', '')
        
        # Validation logic...
        
        if new_email == request.user.email:
            messages.warning(request, "This is already your current email address.")
            return redirect('travellers:dashboard')  # Redirect to dashboard
        
        old_email = request.user.email

        request.user.email = new_email
        request.user.save()

        create_audit_log(
            user=request.user,
            action='email_changed',
            description=f'Changed email from {old_email} to {new_email}'
        )

        messages.success(request, f"Your email has been successfully changed to {new_email}.")
        return redirect('travellers:dashboard')  # Redirect back to dashboard
    
    return render(request, "travellers/change_email.html", {
        'current_email': request.user.email,
    })


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



from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from accounts.models import CustomUser
from .models import Follow, ProfilePost

def follow_list(request, user_id, mode):
    user = get_object_or_404(CustomUser, id=user_id)

    if mode == "followers":
        people = Follow.objects.filter(following=user).select_related("follower")
        title = "Followers"
        people_list = [f.follower for f in people]

    else:  # following
        people = Follow.objects.filter(follower=user).select_related("following")
        title = "Following"
        people_list = [f.following for f in people]

    followers_count = Follow.objects.filter(following=user).count()
    following_count = Follow.objects.filter(follower=user).count()
    posts_count = ProfilePost.objects.filter(user=user).count()

    return render(request, "travellers/follow_list.html", {
        "profile_user": user,
        "people": people_list,
        "mode": mode,
        "title": title,
        "followers_count": followers_count,
        "following_count": following_count,
        "posts_count": posts_count,
    })

# ==================== POST SYSTEM ====================
@login_required
def new_post(request):
    """Handle new post creation from modal (AJAX or normal POST)"""
    if request.method == "POST":
        form = NewPostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.user = request.user
            post.save()
            create_audit_log(
                user=request.user,
                action='post_created',
                description=f'Created a new post (ID: {post.id})'
            )
            
            messages.success(request, "Post created successfully!")
        else:
            messages.error(request, "Please correct the errors below.")
    
    # Redirect back to profile page
    return redirect('travellers:user_profile', user_id=request.user.id)


@login_required
def edit_post(request, post_id):
    """Handle edit post from inline edit button"""
    post = get_object_or_404(ProfilePost, id=post_id)
    
    if post.user != request.user:
        messages.error(request, "You don't have permission to edit this post.")
        return redirect('travellers:user_profile', user_id=request.user.id)
    
    if request.method == "POST":
        form = NewPostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()
            messages.success(request, "Post updated successfully!")
        else:
            messages.error(request, "Please correct the errors below.")
    
    return redirect('travellers:user_profile', user_id=request.user.id)


@login_required
def delete_post(request, post_id):
    """Handle delete post from inline delete button"""
    post = get_object_or_404(ProfilePost, id=post_id)
    
    if post.user == request.user:
        create_audit_log(
            user=request.user,
            action='post_deleted',
            description=f'Deleted post (ID: {post.id})'
        )
        post.delete()
        messages.success(request, "Post deleted successfully!")
    else:
        messages.error(request, "You don't have permission to delete this post.")
    
    return redirect('travellers:user_profile', user_id=request.user.id)

# travellers/views.py - Add these imports at the top
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from .models import ProfilePost, ProfilePostLike, ProfileComment
from community.models import Notification


@login_required
@require_POST
def like_profile_post(request, post_id):
    """Toggle like on a profile post"""
    try:
        post = get_object_or_404(ProfilePost, id=post_id)
        
        # Check if already liked
        existing_like = ProfilePostLike.objects.filter(user=request.user, post=post).first()
        
        if existing_like:
            # Unlike
            existing_like.delete()
            liked = False
            message = "Unliked post"
        else:
            # Like
            ProfilePostLike.objects.create(user=request.user, post=post)
            liked = True
            message = "Liked post"
            
            # Create notification for post owner (if not self)
            if post.user != request.user:
                Notification.objects.create(
                    user=post.user,
                    sender=request.user,
                    notification_type='like',
                    message=f"{request.user.get_full_name() or request.user.username} liked your post"
                )
        
        # Get updated count
        likes_count = post.likes.count()
        
        # Return JSON response
        return JsonResponse({
            'success': True,
            'liked': liked,
            'likes_count': likes_count,
            'message': message
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
@require_POST
def add_profile_comment(request, post_id):
    """Add a comment to a profile post"""
    try:
        post = get_object_or_404(ProfilePost, id=post_id)
        text = request.POST.get('text', '').strip()
        
        if not text:
            return JsonResponse({
                'success': False,
                'error': 'Comment cannot be empty'
            })
        
        # Create comment
        comment = ProfileComment.objects.create(
            post=post,
            user=request.user,
            text=text
        )
        
        # Create notification for post owner
        if post.user != request.user:
            Notification.objects.create(
                user=post.user,
                sender=request.user,
                notification_type='comment',
                message=f"{request.user.get_full_name() or request.user.username} commented on your post: {text[:50]}"
            )
        
        # Get updated comment count
        comments_count = post.comments.count()
        
        # Return JSON response
        return JsonResponse({
            'success': True,
            'comment_id': comment.id,
            'username': request.user.username,
            'user_id': request.user.id,
            'text': comment.text,
            'created_at': comment.created_at.strftime("%b %d, %Y"),
            'comments_count': comments_count
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

# ==================== INBOX ====================
@login_required
def inbox(request):
    from community.models import ChatRoom, Message, Trip, TripParticipant, Notification
    from travellers.models import BuddyRequest
    from accounts.models import CustomUser
    from django.utils import timezone
    from django.shortcuts import get_object_or_404, redirect, render
    from django.http import HttpResponseForbidden
    from django.contrib import messages
    
    # Get all rooms where user is a participant
    rooms = ChatRoom.objects.filter(
        participants=request.user
    ).order_by("-created_at")
    
    # Prepare room data for template
    rooms_data = []
    for room in rooms:
        room_info = {
            'id': room.id,
            'type': room.type,
            'name': room.name,
            'created_at': room.created_at,
            'unread_count': Message.objects.filter(
                room=room,
                is_read=False
            ).exclude(sender=request.user).count(),
        }
        
        # Get last message
        last_msg = room.messages.order_by('-created_at').first()
        room_info['last_message'] = last_msg.text if last_msg else None
        room_info['last_message_time'] = last_msg.created_at if last_msg else None
        
        # Get other participant for DM rooms
        if room.type == 'dm':
            other_participant = room.participants.exclude(id=request.user.id).first()
            if other_participant:
                room_info['other_user'] = {
                    'id': other_participant.id,
                    'username': other_participant.username,
                    'full_name': other_participant.get_full_name() or other_participant.username,
                    'first_letter': other_participant.username[0].upper() if other_participant.username else 'U',
                    'profile_picture': other_participant.profile_picture if hasattr(other_participant, 'profile_picture') else None,
                    'is_online': getattr(other_participant, 'is_online', False),
                }
            else:
                room_info['other_user'] = None
        else:
            room_info['trip_image'] = room.trip.image if hasattr(room, 'trip') and room.trip and hasattr(room.trip, 'image') else None
            room_info['participant_count'] = room.participants.count()
        
        rooms_data.append(room_info)
    
    # Calculate total unread count for badge (This is the key part)
    unread_total = sum(room['unread_count'] for room in rooms_data)
    
    # Handle trip_id parameter (group chat from trip)
    trip_id = request.GET.get("trip_id")
    if trip_id:
        try:
            trip = get_object_or_404(Trip, id=trip_id)
            is_participant = TripParticipant.objects.filter(
                trip=trip,
                user=request.user,
                status='approved'
            ).exists()
            
            if is_participant or trip.creator == request.user:
                chat_room, created = ChatRoom.objects.get_or_create(
                    trip=trip,
                    defaults={
                        'type': 'group',
                        'name': trip.title
                    }
                )
                if created:
                    participants = TripParticipant.objects.filter(
                        trip=trip,
                        status='approved'
                    ).values_list('user', flat=True)
                    chat_room.participants.add(*participants)
                    chat_room.participants.add(trip.creator)
                
                return redirect(f"{request.path}?room={chat_room.id}")
            else:
                messages.error(request, "You don't have access to this trip chat.")
                return redirect("travellers:inbox")
        except Trip.DoesNotExist:
            messages.error(request, "Trip not found.")
            return redirect("travellers:inbox")
    
    # Handle user_id parameter (direct message)
    user_id = request.GET.get("user_id")
    if user_id:
        other_user = get_object_or_404(CustomUser, id=user_id)
        
        # Check if they are buddies (can only message buddies)
        is_buddy = BuddyRequest.objects.filter(
            from_user=request.user,
            to_user=other_user,
            status='accepted'
        ).exists() or BuddyRequest.objects.filter(
            from_user=other_user,
            to_user=request.user,
            status='accepted'
        ).exists()
        
        if not is_buddy and request.user != other_user:
            messages.error(request, "You can only message your buddies. Send a buddy request first.")
            return redirect("travellers:inbox")
        
        # Find or create DM room
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
    
    # Handle room selection
    selected_room_id = request.GET.get("room")
    selected_room = None
    messages_list = []
    selected_room_info = None
    
    if selected_room_id:
        selected_room = get_object_or_404(ChatRoom, id=selected_room_id)
        if request.user not in selected_room.participants.all():
            return HttpResponseForbidden()
        messages_list = selected_room.messages.select_related("sender").order_by("created_at")
        
        # Mark messages as read
        Message.objects.filter(
            room=selected_room,
            is_read=False
        ).exclude(sender=request.user).update(is_read=True, read_at=timezone.now())
        
        # Prepare selected room info
        selected_room_info = {
            'id': selected_room.id,
            'type': selected_room.type,
            'name': selected_room.name,
        }
        
        if selected_room.type == 'dm':
            other_participant = selected_room.participants.exclude(id=request.user.id).first()
            if other_participant:
                selected_room_info['other_user'] = {
                    'id': other_participant.id,
                    'username': other_participant.username,
                    'full_name': other_participant.get_full_name() or other_participant.username,
                    'profile_picture': other_participant.profile_picture if hasattr(other_participant, 'profile_picture') else None,
                }
        
        if selected_room.type == 'group' and hasattr(selected_room, 'trip') and selected_room.trip:
            selected_room_info['trip_image'] = selected_room.trip.image if hasattr(selected_room.trip, 'image') else None
            selected_room_info['participant_count'] = selected_room.participants.count()
    
    # Handle POST message sending
    if request.method == "POST" and selected_room:
        text = request.POST.get("message")
        if text and text.strip():
            Message.objects.create(
                room=selected_room,
                sender=request.user,
                text=text.strip()
            )
            
            # Create notifications for other participants
            for participant in selected_room.participants.exclude(id=request.user.id):
                Notification.objects.create(
                    user=participant,
                    message=f"New message from {request.user.get_full_name() or request.user.username}",
                    notification_type="message",
                    sender=request.user
                )
            
            return redirect(f"{request.path}?room={selected_room.id}")
    
    # ✅ IMPORTANT: Add unread_messages_count to context for the base template
    context = {
        "rooms": rooms_data,
        "unread_total": unread_total,
        "unread_messages_count": unread_total,  # 👈 ADD THIS FOR THE BASE TEMPLATE
        "selected_room": selected_room,
        "selected_room_info": selected_room_info,
        "messages": messages_list,
    }
    
    return render(request, "chat/inbox.html", context)

@login_required
@require_http_methods(["POST"])
def send_message_api(request):
    """API endpoint for sending messages via AJAX"""
    import json
    
    try:
        data = json.loads(request.body)
        room_id = data.get('room_id')
        text = data.get('text', '').strip()
        
        if not text:
            return JsonResponse({'error': 'Message cannot be empty'}, status=400)
        
        room = get_object_or_404(ChatRoom, id=room_id)
        
        if request.user not in room.participants.all():
            return JsonResponse({'error': 'Unauthorized'}, status=403)
        
        message = Message.objects.create(
            room=room,
            sender=request.user,
            text=text
        )
        
        # Create notifications for other participants
        for participant in room.participants.exclude(id=request.user.id):
            Notification.objects.create(
                user=participant,
                message=f"New message from {request.user.username}",
                notification_type="message",
                sender=request.user
            )
        
        return JsonResponse({
            'success': True,
            'message': {
                'id': message.id,
                'text': message.text,
                'sender': message.sender.username,
                'sender_id': message.sender.id,
                'created_at': message.created_at.strftime('%I:%M %p'),
                'is_sender': True
            }
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


from django.http import JsonResponse

@login_required
def pay_advance(request, id):

    booking = get_object_or_404(
        PackageBooking,
        id=id,
        traveller=request.user
    )

    if booking.payment_status != "pending":
        return JsonResponse({
            "success": False,
            "message": "Advance already paid."
        })

    amount = int(booking.advance_amount * 100)

    razorpay_order = client.order.create({
        "amount": amount,
        "currency": "INR",
        "payment_capture": 1
    })

    return JsonResponse({
        "success": True,
        "key": settings.RAZORPAY_KEY_ID,
        "amount": amount,
        "order_id": razorpay_order["id"],
        "booking_id": booking.id,
        "package": booking.package.title,
    })

from django.utils import timezone
import json

@login_required
def advance_payment_success(request, id):

    booking = get_object_or_404(
        PackageBooking,
        id=id,
        traveller=request.user
    )

    data = json.loads(request.body)

    try:

        client.utility.verify_payment_signature({
            "razorpay_order_id": data["razorpay_order_id"],
            "razorpay_payment_id": data["razorpay_payment_id"],
            "razorpay_signature": data["razorpay_signature"]
        })

        # Create payment record
        AgencyPayment.objects.create(
            booking=booking,
            amount=booking.advance_amount,
            payment_type="advance",
            is_paid=True,
            transaction_id=data["razorpay_payment_id"],
            paid_at=timezone.now()
        )

        booking.payment_status = "partial"

        # Generate invoice number on first payment
        if not booking.invoice_number:
            booking.invoice_number = f"INV-{booking.id:06d}"
            booking.invoice_generated_at = timezone.now()

        booking.save()

        create_audit_log(
            user=request.user,
            action='advance_payment_completed',
            description=(
                f'Paid advance amount ₹{booking.advance_amount} '
                f'for package "{booking.package.title}" '
                f'(Booking ID: {booking.id})'
            )
        )

        # Traveller notification
        Notification.objects.create(
            user=request.user,
            notification_type="payment",
            message=f"Advance payment received for {booking.package.title}. Booking confirmed ✅"
        )

        # Agency notification
        Notification.objects.create(
            user=booking.package.agency.user,
            notification_type="payment",
            message=f"{request.user.username} paid the advance amount for {booking.package.title}"
        )

        return JsonResponse({
            "status": "success",
            "booking_id": booking.id,
            "amount": str(booking.advance_amount),
            "payment_type": "Advance Payment"
        })

    except Exception as e:

        return JsonResponse({
            "status": "failed",
            "error": str(e)
        }, status=400)



from django.http import JsonResponse

@login_required
def pay_remaining(request, id):

    booking = get_object_or_404(
        PackageBooking,
        id=id,
        traveller=request.user
    )

    if booking.status != "confirmed":
        return JsonResponse({
            "success": False,
            "message": "Booking not approved yet."
        })

    if booking.payment_status != "partial":
        return JsonResponse({
            "success": False,
            "message": "Advance payment required."
        })

    amount = int(booking.remaining_amount * 100)

    razorpay_order = client.order.create({
        "amount": amount,
        "currency": "INR",
        "payment_capture": 1
    })

    return JsonResponse({
        "success": True,
        "key": settings.RAZORPAY_KEY_ID,
        "amount": amount,
        "order_id": razorpay_order["id"],
        "booking_id": booking.id,
        "package": booking.package.title
    })

from django.utils import timezone
import json

@login_required
def remaining_payment_success(request, id):

    booking = get_object_or_404(
        PackageBooking,
        id=id,
        traveller=request.user
    )

    data = json.loads(request.body)

    try:

        client.utility.verify_payment_signature({
            "razorpay_order_id": data["razorpay_order_id"],
            "razorpay_payment_id": data["razorpay_payment_id"],
            "razorpay_signature": data["razorpay_signature"]
        })

        # Create payment record
        AgencyPayment.objects.create(
            booking=booking,
            amount=booking.remaining_amount,
            payment_type="full",
            is_paid=True,
            transaction_id=data["razorpay_payment_id"],
            paid_at=timezone.now()
        )

        booking.payment_status = "paid"
        booking.remaining_amount = 0

        # Generate invoice number
        if not booking.invoice_number:
            booking.invoice_number = f"INV-{booking.id:06d}"
            booking.invoice_generated_at = timezone.now()

        booking.save()

        create_audit_log(
            user=request.user,
            action='remaining_payment_completed',
            description=(
                f'Completed full payment for package "{booking.package.title}" '
                f'(Booking ID: {booking.id})'
            )
        )

        # Traveller notification
        Notification.objects.create(
            user=request.user,
            notification_type="payment",
            message=f"Full payment completed for {booking.package.title} 🎉"
        )

        # Agency notification
        Notification.objects.create(
            user=booking.package.agency.user,
            notification_type="payment",
            message=f"{request.user.username} completed full payment for {booking.package.title}"
        )

        return JsonResponse({
            "status": "success",
            "booking_id": booking.id,
            "amount": str(booking.total_amount),
            "payment_type": "Full Payment"
        })

    except Exception as e:

        return JsonResponse({
            "status": "failed",
            "error": str(e)
        }, status=400)

from agencies.models import PackageBooking
from restaurants.models import RoomBooking, TableBooking


@login_required
def payment_success_page(request):

    booking_id = request.GET.get("booking")
    booking_type = request.GET.get("booking_type")

    booking = None

    if booking_id and booking_type:

        if booking_type == "package":

            booking = get_object_or_404(
                PackageBooking,
                id=booking_id,
                traveller=request.user
            )

        elif booking_type == "room":

            booking = get_object_or_404(
                RoomBooking,
                id=booking_id,
                user=request.user
            )

        elif booking_type == "table":

            booking = get_object_or_404(
                TableBooking,
                id=booking_id,
                user=request.user
            )

    payment_type = request.GET.get("type", "")
    amount = request.GET.get("amount", "")

    return render(
        request,
        "payments/payment_success.html",
        {
            "booking": booking,
            "booking_type": booking_type,
            "payment_type": payment_type,
            "amount": amount
        }
    )


from django.http import HttpResponse

@login_required
def download_invoice(request, id):

    booking = get_object_or_404(
        PackageBooking,
        id=id,
        traveller=request.user
    )

    pdf_buffer = generate_invoice_pdf(booking)

    response = HttpResponse(
        pdf_buffer,
        content_type="application/pdf"
    )

    response["Content-Disposition"] = (
        f'attachment; filename="invoice_{booking.id}.pdf"'
    )

    return response


from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.models import CustomUser  # Import your custom user model
from .models import TravellerProfile, ProfilePost, CompletedTrip, Follow, BuddyRequest

@login_required
def public_profile(request, user_id):
    """Public profile view for other users with buddy system"""
    
    # Use CustomUser instead of User
    profile_user = get_object_or_404(CustomUser, id=user_id)
    
    if request.user.id == user_id:
        return redirect("travellers:user_profile", user_id=user_id)
    
    try:
        profile = TravellerProfile.objects.get(user=profile_user)
    except TravellerProfile.DoesNotExist:
        messages.error(request, "User profile not found")
        return redirect("travellers:dashboard")
    
    # Check buddy request status
    buddy_request = BuddyRequest.objects.filter(
        from_user=request.user,
        to_user=profile_user
    ).first()
    
    buddy_status = "none"
    buddy_request_obj = None
    
    if buddy_request:
        if buddy_request.status == 'accepted':
            buddy_status = "accepted"
        elif buddy_request.status == 'pending':
            # Check if current user sent the request or received it
            if buddy_request.from_user == request.user:
                buddy_status = "pending_sent"  # User sent the request
            else:
                buddy_status = "pending_received"  # User received the request
                buddy_request_obj = buddy_request
    else:
        # Check if there's a request from the other user to current user
        reverse_request = BuddyRequest.objects.filter(
            from_user=profile_user,
            to_user=request.user,
            status='pending'
        ).first()
        if reverse_request:
            buddy_status = "pending_received"
            buddy_request_obj = reverse_request
    
    # Get posts based on buddy status
    if buddy_status == "accepted":
        posts = ProfilePost.objects.filter(user=profile_user).order_by("-created_at")
        trips = CompletedTrip.objects.filter(user=profile_user, is_shared=True).order_by("-start_date")
    else:
        posts = []
        trips = []
    
    # Get counts (always visible)
    posts_count = ProfilePost.objects.filter(user=profile_user).count()
    trips_count = CompletedTrip.objects.filter(user=profile_user, is_shared=True).count()
    followers_count = Follow.objects.filter(following=profile_user).count()
    following_count = Follow.objects.filter(follower=profile_user).count()

    current_user_profile = TravellerProfile.objects.get(user=request.user)
    
    context = {
        'profile_user': profile_user,
        'profile': profile,
        'posts': posts,
        'trips': trips,
        'posts_count': posts_count,
        'trips_count': trips_count,
        'followers_count': followers_count,
        'following_count': following_count,
        'buddy_status': buddy_status,
        'buddy_request': buddy_request_obj, 
        'user_profile': current_user_profile, # Pass the buddy request object for accept/reject
    }
    
    return render(request, "travellers/public_profile.html", context)


from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Q

from .models import (
    TravellerProfile,
    ProfilePost,
    Follow,
    BuddyRequest
)

@login_required
def search_travellers_page(request):
    """Dedicated page for searching travellers"""

    query = request.GET.get('q', '').strip()

    travellers = []

    if query and len(query) >= 2:

        profiles = TravellerProfile.objects.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(city__icontains=query) |
            Q(state__icontains=query) |
            Q(user__username__icontains=query)
        ).exclude(user=request.user)

        for profile in profiles:

            # ====================================================
            # CHECK BUDDY RELATIONSHIP BOTH SIDES
            # ====================================================

            buddy_request = BuddyRequest.objects.filter(
                Q(from_user=request.user, to_user=profile.user) |
                Q(from_user=profile.user, to_user=request.user)
            ).first()

            buddy_status = "none"

            # ====================================================
            # DETERMINE STATUS
            # ====================================================

            if buddy_request:

                # --------------------------
                # ACCEPTED
                # --------------------------
                if buddy_request.status == "accepted":
                    buddy_status = "accepted"

                # --------------------------
                # PENDING
                # --------------------------
                elif buddy_request.status == "pending":

                    # Current user sent request
                    if buddy_request.from_user == request.user:
                        buddy_status = "sent"

                    # Current user received request
                    else:
                        buddy_status = "received"

                # --------------------------
                # REJECTED
                # --------------------------
                elif buddy_request.status == "rejected":
                    buddy_status = "none"

            travellers.append({
                'user': profile.user,
                'profile': profile,

                'buddy_status': buddy_status,
                'buddy_request': buddy_request,
            })

    context = {
        'query': query,
        'travellers': travellers,
        'results_count': len(travellers),
    }

    return render(
        request,
        "travellers/search_travellers.html",
        context
    )


def search_travellers_api(request):
    """
    API endpoint to search for travellers by username, first_name, last_name, or city
    """
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse({'users': []})
    
    # Search directly in TravellerProfile model
    profiles = TravellerProfile.objects.filter(
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query) |
        Q(city__icontains=query) |
        Q(state__icontains=query)
    ).exclude(user=request.user)[:10]
    
    # Also search in User model for username matches
    users = User.objects.filter(
        Q(username__icontains=query)
    ).exclude(id=request.user.id)
    
    # Combine and deduplicate
    user_ids = set()
    user_data = []
    
    for profile in profiles:
        user_ids.add(profile.user.id)
        avatar_url = profile.profile_picture.url if profile.profile_picture else None
        
        location_parts = []
        if profile.city:
            location_parts.append(profile.city)
        if profile.state:
            location_parts.append(profile.state)
        location = ', '.join(location_parts) if location_parts else ''
        
        initials = ""
        if profile.first_name:
            initials += profile.first_name[0].upper()
        if profile.last_name:
            initials += profile.last_name[0].upper()
        
        user_data.append({
            'id': profile.user.id,
            'username': profile.user.username,
            'full_name': f"{profile.first_name} {profile.last_name}".strip() or profile.user.username,
            'first_name': profile.first_name,
            'last_name': profile.last_name,
            'avatar_url': avatar_url,
            'location': location,
            'initials': initials,
        })
    
    for user in users[:5]:
        if user.id not in user_ids:
            try:
                profile = TravellerProfile.objects.get(user=user)
                avatar_url = profile.profile_picture.url if profile.profile_picture else None
                location_parts = []
                if profile.city:
                    location_parts.append(profile.city)
                if profile.state:
                    location_parts.append(profile.state)
                location = ', '.join(location_parts) if location_parts else ''
                initials = ""
                if profile.first_name:
                    initials += profile.first_name[0].upper()
                if profile.last_name:
                    initials += profile.last_name[0].upper()
                full_name = f"{profile.first_name} {profile.last_name}".strip()
            except TravellerProfile.DoesNotExist:
                avatar_url = None
                location = ''
                initials = user.username[0].upper()
                full_name = user.username
            
            user_data.append({
                'id': user.id,
                'username': user.username,
                'full_name': full_name or user.username,
                'first_name': '',
                'last_name': '',
                'avatar_url': avatar_url,
                'location': location,
                'initials': initials,
            })
    
    return JsonResponse({'users': user_data[:10]})


@login_required
def send_buddy_request(request, user_id):
    """Send a buddy request to another user with notification"""
    
    if request.method == "POST":
        # Use CustomUser instead of User
        to_user = get_object_or_404(CustomUser, id=user_id)
        
        if request.user == to_user:
            messages.error(request, "Cannot send request to yourself")
            return redirect("travellers:public_profile", user_id=user_id)
        
        # Check if request already exists
        existing_request = BuddyRequest.objects.filter(
            from_user=request.user,
            to_user=to_user
        ).first()
        
        if existing_request:
            if existing_request.status == 'pending':
                messages.warning(request, "Request already pending")
            elif existing_request.status == 'accepted':
                messages.info(request, "You are already buddies")
            return redirect("travellers:public_profile", user_id=user_id)
        
        # Create new buddy request
        buddy_request = BuddyRequest.objects.create(
            from_user=request.user,
            to_user=to_user,
            status='pending'
        )
        
        # Create notification
        Notification.objects.create(
            user=to_user,
            sender=request.user,
            notification_type='buddy_request',
            message=f"{request.user.get_full_name() or request.user.username} sent you a buddy request",
            buddy_request=buddy_request
        )
        
        messages.success(request, f"Buddy request sent to {to_user.get_full_name() or to_user.username}!")
        return redirect("travellers:public_profile", user_id=user_id)
    
    return redirect("travellers:dashboard")


@login_required
def accept_buddy_request(request, request_id):
    """Accept a buddy request"""

    buddy_request = get_object_or_404(
        BuddyRequest,
        id=request_id,
        to_user=request.user
    )

    if request.method == "POST":
        # Update request status
        buddy_request.status = 'accepted'
        buddy_request.save()

        # Create follow relationship (both ways for buddies)
        Follow.objects.get_or_create(
            follower=buddy_request.from_user,
            following=buddy_request.to_user
        )
        
        # Also create reverse follow (optional - for mutual following)
        Follow.objects.get_or_create(
            follower=buddy_request.to_user,
            following=buddy_request.from_user
        )

        # Create notification for the sender
        Notification.objects.create(
            user=buddy_request.from_user,
            sender=request.user,
            notification_type='buddy_accepted',
            message=f"{request.user.get_full_name() or request.user.username} accepted your buddy request",
            buddy_request=buddy_request
        )

        messages.success(
            request,
            f"You are now buddies with {buddy_request.from_user.get_full_name() or buddy_request.from_user.username}"
        )

        return redirect("travellers:buddy_requests")

    return redirect("travellers:dashboard")


@login_required
def reject_buddy_request(request, request_id):
    """Reject a buddy request"""
    
    buddy_request = get_object_or_404(BuddyRequest, id=request_id, to_user=request.user)
    
    if request.method == "POST":
        buddy_request.status = 'rejected'
        buddy_request.save()
        
        # Create notification for rejection (optional)
        Notification.objects.create(
            user=buddy_request.from_user,
            sender=request.user,
            notification_type='buddy_rejected',
            message=f"{request.user.get_full_name() or request.user.username} declined your buddy request",
            buddy_request=buddy_request
        )
        
        messages.info(request, f"Buddy request from {buddy_request.from_user.get_full_name() or buddy_request.from_user.username} rejected.")
        return redirect("travellers:buddy_requests")
    
    return redirect("travellers:dashboard")


@login_required
def cancel_buddy_request(request, request_id):
    """Cancel a sent buddy request"""
    
    buddy_request = get_object_or_404(BuddyRequest, id=request_id, from_user=request.user, status='pending')
    
    if request.method == "POST":
        buddy_request.delete()
        messages.success(request, "Buddy request cancelled.")
        return redirect("travellers:buddy_requests")
    
    return redirect("travellers:dashboard")


@login_required
def buddy_requests(request):
    """View all buddy requests - central management page"""
    
    # Received requests (others want to connect with me)
    received_requests = BuddyRequest.objects.filter(
        to_user=request.user, 
        status='pending'
    ).select_related('from_user')
    
    # Sent requests (I want to connect with others)
    sent_requests = BuddyRequest.objects.filter(
        from_user=request.user
    ).select_related('to_user').order_by('-created_at')
    
    # Count pending for badge notification
    pending_count = received_requests.count()
    
    context = {
        'received_requests': received_requests,
        'sent_requests': sent_requests,
        'pending_count': pending_count,
    }
    
    return render(request, "travellers/buddy_requests.html", context)


@login_required
def remove_buddy(request, user_id):
    """Remove a buddy (unfollow and delete buddy relationship)"""
    
    if request.method == "POST":
        buddy_user = get_object_or_404(CustomUser, id=user_id)
        
        # Remove follow relationships
        Follow.objects.filter(follower=request.user, following=buddy_user).delete()
        Follow.objects.filter(follower=buddy_user, following=request.user).delete()
        
        # Delete or mark as rejected the buddy request
        buddy_request = BuddyRequest.objects.filter(
            from_user=request.user,
            to_user=buddy_user,
            status='accepted'
        ).first()
        
        if not buddy_request:
            buddy_request = BuddyRequest.objects.filter(
                from_user=buddy_user,
                to_user=request.user,
                status='accepted'
            ).first()
        
        if buddy_request:
            buddy_request.status = 'rejected'
            buddy_request.save()
        
        messages.success(request, f"Removed {buddy_user.get_full_name() or buddy_user.username} from your buddies")
        return redirect("travellers:buddy_requests")
    
    return redirect("travellers:dashboard")

@login_required
def add_package_review(request, booking_id):

    booking = get_object_or_404(
        PackageBooking,
        id=booking_id,
        traveller=request.user
    )

    if not booking.can_review:
        messages.error(request, "You can review only after completing the trip.")
        return redirect("travellers:my_bookings")

    if hasattr(booking, "review"):
        messages.error(request, "You already reviewed this trip.")
        return redirect("travellers:my_bookings")

    if request.method == "POST":

        rating = request.POST.get("rating")
        review_text = request.POST.get("review")

        PackageReview.objects.create(
            booking=booking,
            traveller=request.user,
            package=booking.package,
            agency=booking.package.agency,
            rating=rating,
            review=review_text
        )

        messages.success(request, "Review added successfully.")

    return redirect("travellers:my_bookings")

from django.shortcuts import get_object_or_404, render
from django.db import models
from agencies.models import AgencyProfile
from agencies.models import TourPackage  # Import TourPackage model

def agency_detail(request, agency_id):
    """View agency details and their packages"""
    agency = get_object_or_404(AgencyProfile, id=agency_id)
    
    # Get all packages from this agency - using the correct relationship
    # Try different possible relationship names
    try:
        # Try to get packages using the related_name from TourPackage model
        if hasattr(agency, 'tour_packages'):
            packages = agency.tour_packages.filter(is_active=True).order_by('-created_at')
        elif hasattr(agency, 'packages'):
            packages = agency.packages.filter(is_active=True).order_by('-created_at')
        else:
            # If no direct relation, try to get through the agency field
            packages = TourPackage.objects.filter(agency=agency, is_active=True).order_by('-created_at')
    except:
        packages = TourPackage.objects.filter(agency=agency, is_active=True).order_by('-created_at')
    
    # Get agency stats
    total_packages = packages.count() if hasattr(packages, 'count') else 0
    
    # Calculate total bookings (if bookings field exists)
    total_bookings = 0
    for pkg in packages:
        if hasattr(pkg, 'bookings_count'):
            total_bookings += pkg.bookings_count or 0
    
    # Get average rating (if rating field exists)
    avg_rating = getattr(agency, 'average_rating', 0) or 0
    
    context = {
        'agency': agency,
        'packages': packages[:6] if packages else [],  # Show latest 6 packages
        'total_packages': total_packages,
        'total_bookings': total_bookings,
        'avg_rating': avg_rating,
    }
    
    return render(request, 'travellers/agency_detail.html', context)

# Add these imports at the top
from datetime import datetime, timedelta
from django.utils import timezone

from datetime import datetime, timedelta
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json

def api_table_slots(request):
    """Get available time slots for a table on a specific date"""
    table_id = request.GET.get('table_id')
    date_str = request.GET.get('date')
    
    print(f"API called - table_id: {table_id}, date: {date_str}")  # Debug
    
    if not table_id or not date_str:
        return JsonResponse({'slots': [], 'error': 'Missing parameters'})
    
    try:
        table = get_object_or_404(Table, id=table_id)
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        # Generate time slots from 12 PM to 10 PM (1 hour intervals)
        slots = []
        for hour in range(12, 22):  # 12 PM to 10 PM
            slot_time = f"{hour}:00"
            am_pm = "PM" if hour >= 12 else "AM"
            display_hour = hour if hour <= 12 else hour - 12
            display_time = f"{display_hour}:00 {am_pm}"
            
            slot_start = datetime.combine(date, datetime.strptime(f"{hour}:00", "%H:%M").time())
            slot_end = slot_start + timedelta(hours=1)
            
            # Check if slot is already booked
            is_booked = TableBooking.objects.filter(
                table=table,
                start_time__lt=slot_end,
                end_time__gt=slot_start,
                status__in=['pending', 'confirmed']
            ).exists()
            
            slots.append({
                'start': slot_start.strftime('%Y-%m-%d %H:%M:%S'),
                'end': slot_end.strftime('%Y-%m-%d %H:%M:%S'),
                'time': display_time,
                'is_booked': is_booked
            })
        
        return JsonResponse({'slots': slots, 'success': True})
        
    except Exception as e:
        print(f"Error in api_table_slots: {str(e)}")  # Debug
        return JsonResponse({'slots': [], 'error': str(e)}, status=500)


def api_table_details(request, table_id):
    """Get table details API endpoint"""
    try:
        table = get_object_or_404(Table, id=table_id)
        
        data = {
            'id': table.id,
            'table_number': table.table_number,
            'capacity': table.capacity,
            'zone': table.zone,
            'has_ac': table.has_ac,
            'has_view': table.has_view,
            'has_music': table.has_music,
            'smoking_allowed': table.smoking_allowed,
            'is_active': table.is_active,
            'pos_x': table.pos_x,
            'pos_y': table.pos_y,
            'width': table.width,
            'height': table.height,
            'shape': table.shape,
            'rotation': table.rotation,
        }
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=404)


@login_required
def book_table_from_layout(request):
    """Book a table from the layout view"""
    if request.method != "POST":
        return JsonResponse({'success': False, 'error': 'Invalid request method'})
    
    table_id = request.POST.get('table_id')
    guests = request.POST.get('guests')
    date = request.POST.get('booking_date')
    start_time = request.POST.get('start_time')
    end_time = request.POST.get('end_time')
    special_request = request.POST.get('special_request', '')
    
    if not all([table_id, guests, date, start_time, end_time]):
        return JsonResponse({'success': False, 'error': 'Missing required fields'})
    
    try:
        table = get_object_or_404(Table, id=table_id)
        
        # Parse datetime
        start_datetime = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
        end_datetime = datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')
        
        # Check capacity
        if int(guests) > table.capacity:
            return JsonResponse({'success': False, 'error': f'Table capacity is only {table.capacity} guests'})
        
        # Check for conflicts
        conflict = TableBooking.objects.filter(
            table=table,
            status__in=['pending', 'confirmed'],
            start_time__lt=end_datetime,
            end_time__gt=start_datetime
        ).exists()
        
        if conflict:
            return JsonResponse({'success': False, 'error': 'This time slot is already booked'})
        
        # Create booking
        booking = TableBooking.objects.create(
            table=table,
            user=request.user,
            start_time=start_datetime,
            end_time=end_datetime,
            guests=int(guests),
            special_request=special_request,
            status='pending'
        )
        
        # Check if advance payment required
        if table.restaurant.requires_table_advance:
            return JsonResponse({
                'success': True, 
                'redirect_url': reverse('travellers:table_booking_payment', args=[booking.id])
            })
        else:
            booking.status = 'confirmed'
            booking.save()
            return JsonResponse({
                'success': True,
                'redirect_url': reverse('travellers:my_bookings')
            })
            
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def select_table(request, pk):
    """View to select a table from floor plan"""
    property_obj = get_object_or_404(RestaurantProfile, id=pk, is_approved=True)
    
    if not property_obj.has_table_service:
        messages.error(request, "Table service is not available at this property.")
        return redirect('travellers:restaurant_detail', pk=pk)
    
    tables = Table.objects.filter(
        restaurant=property_obj,
        is_active=True,
        is_reservable=True
    )
    
    # Get today's bookings to mark booked tables
    today = timezone.now().date()
    for table in tables:
        table.is_booked = TableBooking.objects.filter(
            table=table,
            start_time__date=today,
            status__in=['pending', 'confirmed']
        ).exists()
    
    context = {
        'property': property_obj,
        'tables': tables,
    }
    
    return render(request, 'travellers/select_table.html', context)