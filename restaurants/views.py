# restaurants/views.py - CLEANED VERSION (Remove duplicates)

from datetime import timezone
from multiprocessing import context
from django.contrib.auth.decorators import login_required
from django.db import models
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.urls import reverse
from django.http import HttpResponseRedirect, JsonResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Count
from django.db.models import Sum
from django.db.models.functions import TruncMonth
import json
from restaurants.utils import auto_complete_room_bookings

from restaurants.models import (
    RestaurantProfile, Review, Table, TableBooking, TableSlot,
    RoomType, RoomTypeDetail, Room, RoomBooking, PropertyMedia, CancellationPolicy
)
from restaurants.forms import (
    RestaurantProfileForm, ReviewForm, TableForm, RoomTypeForm, 
    RoomTypeDetailForm, PropertyMediaForm
)
from admin_app.utils import create_audit_log


@login_required
def manage_property(request):
    """Comprehensive property management view"""
    restaurant = request.user.restaurantprofile
    
    tables = Table.objects.filter(restaurant=restaurant)
    room_types = RoomType.objects.filter(restaurant=restaurant).prefetch_related('rooms', 'detail', 'cancellation_policy')
    media_files = PropertyMedia.objects.filter(restaurant=restaurant)
    
    action = request.POST.get('action')
    
    # Profile update
    if request.method == "POST" and action == 'update_profile':
        form = RestaurantProfileForm(request.POST, request.FILES, instance=restaurant)
        if form.is_valid():
            form.save()
            create_audit_log(
                user=request.user,
                action='restaurant_profile_updated',
                description=f'Updated restaurant profile: {restaurant.restaurant_name}'
            )
            messages.success(request, "Property profile updated successfully!")
            return HttpResponseRedirect(reverse('manage_property'))
        else:
            messages.error(request, "Please correct the errors below.")
    
    # Table addition
    elif request.method == "POST" and action == 'add_table':
        form = TableForm(request.POST)
        if form.is_valid():
            table = form.save(commit=False)
            table.restaurant = restaurant
            table.pos_x = 100
            table.pos_y = 100
            table.width = 80
            table.height = 80
            table.shape = 'square'
            table.rotation = 0
            table.save()
            create_audit_log(
                user=request.user,
                action='table_added',
                description=f'Added table {table.table_number}'
            )
            messages.success(request, f"Table {table.table_number} added successfully!")
            return HttpResponseRedirect(reverse('manage_property') + '?tab=tables')
        else:
            messages.error(request, "Please correct the errors below.")
    
    # Room type addition with details and cancellation policy
    elif request.method == "POST" and action == 'add_room_type':
        try:
            # Create the room type
            room_type = RoomType.objects.create(
                restaurant=restaurant,
                name=request.POST.get('name'),
                variant=request.POST.get('variant'),
                price_per_night=request.POST.get('price_per_night'),
                max_guests=request.POST.get('max_guests')
            )
            
            # Create the room detail
            room_detail = RoomTypeDetail.objects.create(
                room_type=room_type,
                size_sqft=request.POST.get('size_sqft') or None,
                view=request.POST.get('view'),
                bed_type=request.POST.get('bed_type'),
                bathrooms=request.POST.get('bathrooms') or 1,
                about_room=request.POST.get('about_room'),
                other_amenities=request.POST.get('other_amenities'),
                wifi=request.POST.get('wifi') == 'on',
                smoking_allowed=request.POST.get('smoking_allowed') == 'on',
                couple_friendly=request.POST.get('couple_friendly') == 'on',
                tv=request.POST.get('tv') == 'on',
                air_conditioning=request.POST.get('air_conditioning') == 'on',
                mineral_water=request.POST.get('mineral_water') == 'on',
                laundry_service=request.POST.get('laundry_service') == 'on',
                housekeeping=request.POST.get('housekeeping') == 'on',
                in_room_dining=request.POST.get('in_room_dining') == 'on',
                iron_ironing_board=request.POST.get('iron_ironing_board') == 'on',
                room_service=request.POST.get('room_service') == 'on'
            )
            
            # Create cancellation policy
            policy_type = request.POST.get('cancellation_policy_type', 'standard')
            free_until_days = request.POST.get('free_until_days', 7)
            refund_percentage_after = request.POST.get('refund_percentage_after', 30)
            
            # Import CancellationPolicy at the top of your file
            from restaurants.models import CancellationPolicy
            
            CancellationPolicy.objects.create(
                room_type=room_type,
                policy_type=policy_type,
                free_until_days=int(free_until_days),
                refund_percentage_after=int(refund_percentage_after)
            )
            
            create_audit_log(
                user=request.user,
                action='room_type_added',
                description=f'Added room type: {room_type.name}'
            )

            messages.success(request, f"Room type '{room_type.name}' with full details added successfully!")
            
        except Exception as e:
            messages.error(request, f"Error creating room type: {str(e)}")
        
        return HttpResponseRedirect(reverse('manage_property') + '?tab=rooms')
    
    # Media upload
    elif request.method == "POST" and action == 'upload_media':
        section = request.POST.get('section')
        room_type_id = request.POST.get('room_type')
        common_title = request.POST.get('common_title', '')
        images = request.FILES.getlist('images')
        
        if not section:
            messages.error(request, "Please select a section for the images.")
        elif not images:
            messages.error(request, "Please select at least one image to upload.")
        else:
            uploaded_count = 0
            error_count = 0
            
            for image in images:
                try:
                    if image.size > 5 * 1024 * 1024:
                        error_count += 1
                        continue
                    
                    valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
                    import os
                    ext = os.path.splitext(image.name)[1].lower()
                    if ext not in valid_extensions:
                        error_count += 1
                        continue
                    
                    media = PropertyMedia.objects.create(
                        restaurant=restaurant,
                        section=section,
                        title=common_title or image.name,
                        image=image
                    )
                    
                    if room_type_id and room_type_id != '':
                        try:
                            room_type = RoomType.objects.get(id=room_type_id, restaurant=restaurant)
                            media.room_type = room_type
                            media.save()
                        except RoomType.DoesNotExist:
                            pass
                    
                    uploaded_count += 1
                    
                except Exception as e:
                    error_count += 1
                    print(f"Error uploading {image.name}: {str(e)}")
            
            if uploaded_count > 0:
                messages.success(request, f"Successfully uploaded {uploaded_count} image(s)!")
            if error_count > 0:
                messages.warning(request, f"{error_count} image(s) failed to upload.")
        
        return HttpResponseRedirect(reverse('manage_property') + '?tab=media')
    
    # Initialize forms
    profile_form = RestaurantProfileForm(instance=restaurant)
    table_form = TableForm()
    room_type_form = RoomTypeForm()
    room_detail_form = RoomTypeDetailForm()
    media_form = PropertyMediaForm()
    
    for index, table in enumerate(tables):
        table.preview_left = (index % 4) * 70 + 20
        table.preview_top = (index // 4) * 70 + 20
    
    context = {
        'restaurant': restaurant,
        'profile_form': profile_form,
        'table_form': table_form,
        'room_type_form': room_type_form,
        'room_detail_form': room_detail_form,
        'media_form': media_form,
        'tables': tables,
        'room_types': room_types,
        'media_files': media_files,
    }
    
    return render(request, "restaurants/manage_property.html", context)


# ==================== DELETE VIEWS ====================

@login_required
def delete_table(request, id):
    restaurant = request.user.restaurantprofile
    table = get_object_or_404(Table, id=id, restaurant=restaurant)
    table_number = table.table_number
    create_audit_log(
        user=request.user,
        action='table_deleted',
        description=f'Deleted table {table.table_number}'
    )
    table.delete()
    messages.success(request, f"Table {table_number} deleted successfully!")
    return HttpResponseRedirect(reverse('manage_property') + '?tab=tables')


@login_required
def delete_room_type(request, id):
    restaurant = request.user.restaurantprofile
    room_type = get_object_or_404(RoomType, id=id, restaurant=restaurant)
    room_type_name = room_type.name
    create_audit_log(
        user=request.user,
        action='room_type_deleted',
        description=f'Deleted room type: {room_type.name}'
    )
    room_type.delete()
    messages.success(request, f"Room type '{room_type_name}' deleted successfully!")
    return HttpResponseRedirect(reverse('manage_property') + '?tab=rooms')


@login_required
def delete_media(request, id):
    restaurant = request.user.restaurantprofile
    media = get_object_or_404(PropertyMedia, id=id, restaurant=restaurant)
    media.delete()
    messages.success(request, "Media deleted successfully!")
    return HttpResponseRedirect(reverse('manage_property') + '?tab=media')


# ==================== ROOM MANAGEMENT (for individual rooms) ====================

@login_required
def add_room(request, room_type_id):
    """Add a new room to a room type"""
    restaurant = request.user.restaurantprofile
    room_type = get_object_or_404(RoomType, id=room_type_id, restaurant=restaurant)
    
    if request.method == "POST":
        room_number = request.POST.get('room_number')
        status = request.POST.get('status', 'available')
        
        if room_number:
            room = Room.objects.create(
                room_type=room_type,
                room_number=room_number,
                status=status
            )
            create_audit_log(
                user=request.user,
                action='room_added',
                description=f'Added room {room.room_number} ({room_type.name})'
            )
            messages.success(request, f"Room {room_number} added successfully!")
        else:
            messages.error(request, "Room number is required.")
        
        return HttpResponseRedirect(reverse('manage_property') + '?tab=rooms')
    
    return HttpResponseRedirect(reverse('manage_property') + '?tab=rooms')


@login_required
def edit_room(request, room_id):
    """Edit individual room details"""
    restaurant = request.user.restaurantprofile
    room = get_object_or_404(Room, id=room_id, room_type__restaurant=restaurant)
    
    if request.method == "POST":
        room_number = request.POST.get('room_number')
        status = request.POST.get('status')
        
        if room_number:
            room.room_number = room_number
            room.status = status
            room.save()
            create_audit_log(
                user=request.user,
                action='room_updated',
                description=f'Updated room {room.room_number}'
            )
            messages.success(request, f"Room {room_number} updated successfully!")
        else:
            messages.error(request, "Room number is required.")
        
        return HttpResponseRedirect(reverse('manage_property') + '?tab=rooms')
    
    return HttpResponseRedirect(reverse('manage_property') + '?tab=rooms')


@login_required
def delete_room(request, room_id):
    """Delete a room"""
    restaurant = request.user.restaurantprofile
    room = get_object_or_404(Room, id=room_id, room_type__restaurant=restaurant)
    room_number = room.room_number
    create_audit_log(
        user=request.user,
        action='room_deleted',
        description=f'Deleted room {room.room_number}'
    )
    room.delete()
    messages.success(request, f"Room {room_number} deleted successfully!")
    return HttpResponseRedirect(reverse('manage_property') + '?tab=rooms')


# ==================== API ENDPOINTS ====================

@login_required
@require_http_methods(["GET"])
def api_room_type_detail(request, room_type_id):
    """API endpoint for fetching room type details (used by modal)"""
    try:
        restaurant = request.user.restaurantprofile
        room_type = get_object_or_404(RoomType, id=room_type_id, restaurant=restaurant)
        detail, created = RoomTypeDetail.objects.get_or_create(room_type=room_type)
        
        data = {
            'id': room_type.id,
            'name': room_type.name,
            'variant': room_type.variant,
            'price_per_night': float(room_type.price_per_night),
            'max_guests': room_type.max_guests,
            'size_sqft': detail.size_sqft,
            'view': detail.view,
            'bed_type': detail.bed_type,
            'bathrooms': detail.bathrooms,
            'about_room': detail.about_room,
            'cancellation_policy': detail.cancellation_policy,
            'other_amenities': detail.other_amenities,
            'wifi': detail.wifi,
            'smoking_allowed': detail.smoking_allowed,
            'couple_friendly': detail.couple_friendly,
            'tv': detail.tv,
            'air_conditioning': detail.air_conditioning,
            'mineral_water': detail.mineral_water,
            'laundry_service': detail.laundry_service,
            'housekeeping': detail.housekeeping,
            'in_room_dining': detail.in_room_dining,
            'iron_ironing_board': detail.iron_ironing_board,
            'room_service': detail.room_service,
        }
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=404)


@login_required
def edit_room_type(request, room_type_id):
    """Handle form submission for editing room type"""
    restaurant = request.user.restaurantprofile
    room_type = get_object_or_404(RoomType, id=room_type_id, restaurant=restaurant)
    
    if request.method == "POST":
        # Update room type basic info
        room_type.name = request.POST.get('name')
        room_type.variant = request.POST.get('variant')
        room_type.price_per_night = request.POST.get('price_per_night')
        room_type.max_guests = request.POST.get('max_guests')
        room_type.save()
        
        # Update room type details
        detail, created = RoomTypeDetail.objects.get_or_create(room_type=room_type)
        detail.size_sqft = request.POST.get('size_sqft') or None
        detail.view = request.POST.get('view')
        detail.bed_type = request.POST.get('bed_type')
        detail.bathrooms = request.POST.get('bathrooms') or 1
        detail.about_room = request.POST.get('about_room')
        detail.other_amenities = request.POST.get('other_amenities')
        detail.wifi = request.POST.get('wifi') == 'on'
        detail.smoking_allowed = request.POST.get('smoking_allowed') == 'on'
        detail.couple_friendly = request.POST.get('couple_friendly') == 'on'
        detail.tv = request.POST.get('tv') == 'on'
        detail.air_conditioning = request.POST.get('air_conditioning') == 'on'
        detail.mineral_water = request.POST.get('mineral_water') == 'on'
        detail.laundry_service = request.POST.get('laundry_service') == 'on'
        detail.housekeeping = request.POST.get('housekeeping') == 'on'
        detail.in_room_dining = request.POST.get('in_room_dining') == 'on'
        detail.iron_ironing_board = request.POST.get('iron_ironing_board') == 'on'
        detail.room_service = request.POST.get('room_service') == 'on'
        detail.save()
        
        # Update cancellation policy
        policy_type = request.POST.get('cancellation_policy_type')
        free_until_days = request.POST.get('free_until_days')
        refund_percentage_after = request.POST.get('refund_percentage_after')
        
        if policy_type:
            # Get or create cancellation policy for this room type
            cancellation_policy, created = CancellationPolicy.objects.get_or_create(
                room_type=room_type
            )
            cancellation_policy.policy_type = policy_type
            cancellation_policy.free_until_days = int(free_until_days) if free_until_days else 7
            cancellation_policy.refund_percentage_after = int(refund_percentage_after) if refund_percentage_after else 30
            cancellation_policy.save()
        
        messages.success(request, f"Room type '{room_type.name}' updated successfully!")
        return HttpResponseRedirect(reverse('manage_property') + '?tab=rooms')
    
    return HttpResponseRedirect(reverse('manage_property') + '?tab=rooms')


# ==================== TABLE LAYOUT ====================

@login_required
def manage_table_layout(request):
    restaurant = request.user.restaurantprofile
    
    if not restaurant.has_table_service:
        messages.warning(request, "Please enable Table Service first.")
        return redirect('manage_property?tab=profile')
    
    tables = Table.objects.filter(restaurant=restaurant).order_by('table_number')
    
    context = {
        'restaurant': restaurant,
        'tables': tables,
    }
    
    return render(request, "restaurants/manage_table_layout.html", context)


@login_required
@require_http_methods(["GET", "POST"])
def api_table_crud(request, table_id=None):
    """API for CRUD operations on tables"""
    restaurant = request.user.restaurantprofile
    
    # GET single table
    if request.method == "GET" and table_id:
        try:
            table = Table.objects.get(id=table_id, restaurant=restaurant)
            data = {
                'id': table.id,
                'table_number': table.table_number,
                'capacity': table.capacity,
                'shape': table.shape,
                'section_name': table.section_name,
                'is_active': table.is_active,
                'pos_x': table.pos_x,
                'pos_y': table.pos_y,
                'width': table.width,
                'height': table.height,
                'rotation': table.rotation,
            }
            return JsonResponse(data)
        except Table.DoesNotExist:
            return JsonResponse({'error': 'Table not found'}, status=404)
    
    # POST add new table
    elif request.method == "POST" and not table_id:
        try:
            data = json.loads(request.body)
            table = Table.objects.create(
                restaurant=restaurant,
                table_number=f"T{Table.objects.filter(restaurant=restaurant).count() + 1}",
                capacity=data.get('capacity', 2),
                pos_x=data.get('pos_x', 100),
                pos_y=data.get('pos_y', 100),
                width=data.get('width', 80),
                height=data.get('height', 80),
                shape=data.get('shape', 'square'),
            )
            return JsonResponse({'success': True, 'table_id': table.id})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    
    # POST update table
    elif request.method == "POST" and table_id:
        try:
            data = json.loads(request.body)
            table = Table.objects.get(id=table_id, restaurant=restaurant)
            table.table_number = data.get('table_number', table.table_number)
            table.capacity = data.get('capacity', table.capacity)
            table.shape = data.get('shape', table.shape)
            table.section_name = data.get('section_name', table.section_name)
            table.is_active = data.get('is_active', table.is_active)
            table.pos_x = data.get('pos_x', table.pos_x)
            table.pos_y = data.get('pos_y', table.pos_y)
            table.width = data.get('width', table.width)
            table.height = data.get('height', table.height)
            table.rotation = data.get('rotation', table.rotation)
            table.save()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    
    # DELETE table
    elif request.method == "DELETE" and table_id:
        try:
            table = Table.objects.get(id=table_id, restaurant=restaurant)
            table.delete()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Invalid request'}, status=400)


@login_required
@require_http_methods(["POST"])
def api_bulk_update_layout(request):
    try:
        data = json.loads(request.body)
        restaurant = request.user.restaurantprofile
        
        for table_data in data.get('tables', []):
            Table.objects.filter(
                id=table_data['id'],
                restaurant=restaurant
            ).update(
                pos_x=table_data.get('left', 0),
                pos_y=table_data.get('top', 0),
                width=table_data.get('width', 80),
                height=table_data.get('height', 80),
                rotation=table_data.get('rotation', 0)
            )
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


# ==================== REVIEWS ====================

@login_required
def leave_review(request, restaurant_id):
    restaurant = get_object_or_404(RestaurantProfile, id=restaurant_id)
    
    existing_review = Review.objects.filter(user=request.user, restaurant=restaurant).first()
    if existing_review:
        messages.warning(request, "You have already reviewed this property.")
        return redirect('travellers:restaurant_detail', pk=restaurant_id)
    
    # Check for completed bookings...
    # (keep your existing leave_review logic)
    
    return render(request, 'restaurants/leave_review.html', context)


@login_required
def edit_review(request, review_id):
    # Keep your existing edit_review logic
    pass


@login_required
def delete_review(request, review_id):
    # Keep your existing delete_review logic
    pass


def update_restaurant_rating(restaurant):
    reviews = restaurant.reviews.all()
    total_reviews = reviews.count()
    
    if total_reviews > 0:
        avg_rating = reviews.aggregate(models.Avg('rating'))['rating__avg']
        restaurant.avg_rating = round(avg_rating, 1)
        restaurant.total_reviews = total_reviews
    else:
        restaurant.avg_rating = 0.0
        restaurant.total_reviews = 0
    
    restaurant.save()


@login_required
def restaurant_dashboard(request):
    from django.db.models import Sum
    from django.db.models.functions import TruncMonth
    auto_complete_room_bookings()
    restaurant = request.user.restaurantprofile
    
    # Basic Counts
    total_tables = Table.objects.filter(restaurant=restaurant).count()
    total_rooms = Room.objects.filter(room_type__restaurant=restaurant).count()
    total_images = PropertyMedia.objects.filter(restaurant=restaurant).count()
    
    # Bookings
    room_bookings = RoomBooking.objects.filter(room__room_type__restaurant=restaurant)
    table_bookings = TableBooking.objects.filter(table__restaurant=restaurant)
    
    total_bookings = room_bookings.count() + table_bookings.count()
    
    recent_room_bookings = room_bookings.order_by("-created_at")[:5]
    recent_table_bookings = table_bookings.order_by("-start_time")[:5]
    
    # Revenue
    room_revenue = room_bookings.filter(
        status__in=["confirmed", "completed"]
    ).aggregate(total=Sum("total_amount"))["total"] or 0
    
    table_revenue = table_bookings.filter(
        status__in=["confirmed", "completed"]
    ).aggregate(total=Sum("advance_paid"))["total"] or 0
    
    total_revenue = room_revenue + table_revenue
    
    # Pie Chart Data
    pie_labels = ["Room Revenue", "Table Revenue"]
    pie_data = [float(room_revenue), float(table_revenue)]
    
    # Monthly Revenue
    monthly_rooms = room_bookings.filter(
        status__in=["confirmed", "completed"]
    ).annotate(
        month=TruncMonth("created_at")
    ).values("month").annotate(
        revenue=Sum("total_amount")
    ).order_by("month")
    
    month_labels = []
    month_values = []
    
    for item in monthly_rooms:
        if item["month"]:
            month_labels.append(item["month"].strftime("%b %Y"))
            month_values.append(float(item["revenue"]))
    
    context = {
        "restaurant": restaurant,
        "total_tables": total_tables,
        "total_rooms": total_rooms,
        "total_images": total_images,
        "total_bookings": total_bookings,
        "room_revenue": room_revenue,
        "table_revenue": table_revenue,
        "total_revenue": total_revenue,
        "recent_room_bookings": recent_room_bookings,
        "recent_table_bookings": recent_table_bookings,
        "pie_labels": json.dumps(pie_labels),
        "pie_data": json.dumps(pie_data),
        "month_labels": json.dumps(month_labels),
        "month_values": json.dumps(month_values),
    }
    
    return render(request, "restaurants/dashboard.html", context)


@login_required
def bookings(request):

    restaurant = request.user.restaurantprofile

    room_bookings = RoomBooking.objects.filter(
        room__room_type__restaurant=restaurant
    ).select_related(
        "user",
        "room",
        "room__room_type"
    ).order_by("-created_at")

    table_bookings = TableBooking.objects.filter(
        table__restaurant=restaurant
    ).select_related(
        "user",
        "table"
    ).order_by("-start_time")

    context = {
        "restaurant": restaurant,  # Add this line
        "room_bookings": room_bookings,
        "table_bookings": table_bookings,

        "room_confirmed": room_bookings.filter(
            status="confirmed"
        ).count(),

        "room_cancelled": room_bookings.filter(
            status="cancelled"
        ).count(),

        "room_completed": room_bookings.filter(
            status="completed"
        ).count(),

        "table_confirmed": table_bookings.filter(
            status="confirmed"
        ).count(),

        "table_cancelled": table_bookings.filter(
            status="cancelled"
        ).count(),

        "table_completed": table_bookings.filter(
            status="completed"
        ).count(),
    }

    return render(
        request,
        "restaurants/bookings.html",
        context
    )

@login_required
def complete_room_booking(request, booking_id):

    booking = get_object_or_404(
        RoomBooking,
        id=booking_id,
        room__room_type__restaurant__user=request.user
    )

    booking.status = "completed"
    booking.save()

    create_audit_log(
        user=request.user,
        action='room_booking_completed',
        description=f'Completed room booking #{booking.id}'
    )

    messages.success(
        request,
        "Room booking marked as completed."
    )

    return redirect("bookings")


@login_required
def complete_table_booking(request, booking_id):

    booking = get_object_or_404(
        TableBooking,
        id=booking_id,
        table__restaurant__user=request.user
    )

    booking.status = "completed"
    booking.save()

    create_audit_log(
        user=request.user,
        action='table_booking_completed',
        description=f'Completed table booking #{booking.id}'
    )

    messages.success(
        request,
        "Table booking marked as completed."
    )

    return redirect("bookings")


import traceback

@login_required
@require_http_methods(["GET"])
def api_booking_details(request, booking_type, booking_id):
    """API endpoint to get booking details for modal"""
    try:
        restaurant = request.user.restaurantprofile
        
        if booking_type == 'room':
            booking = get_object_or_404(
                RoomBooking,
                id=booking_id,
                room__room_type__restaurant=restaurant
            )
            
            data = {
                'success': True,
                'id': booking.id,
                'guest_name': booking.user.get_full_name() or booking.user.username,
                'guest_email': booking.user.email,
                'room_type': booking.room.room_type.name,
                'room_number': booking.room.room_number,
                'check_in': booking.check_in.strftime('%b %d, %Y'),
                'check_out': booking.check_out.strftime('%b %d, %Y'),
                'nights': booking.nights,
                'guests': booking.guests,
                'adults': booking.adults,
                'children': booking.children,
                'total_amount': float(booking.total_amount) if booking.total_amount else 0,
                'status': booking.status,
                'status_display': booking.get_status_display(),
                'special_request': booking.special_request or '',
                'created_at': booking.created_at.strftime('%b %d, %Y %I:%M %p'),
                'price_per_night': float(booking.price_per_night) if booking.price_per_night else 0,
            }
            
        elif booking_type == 'table':
            booking = get_object_or_404(
                TableBooking,
                id=booking_id,
                table__restaurant=restaurant
            )
            
            data = {
                'success': True,
                'id': booking.id,
                'guest_name': booking.user.get_full_name() or booking.user.username,
                'guest_email': booking.user.email,
                'table_number': booking.table.table_number,
                'zone': booking.table.zone or 'General',
                'capacity': booking.table.capacity,
                'start_time': booking.start_time.strftime('%b %d, %Y at %I:%M %p'),
                'end_time': booking.end_time.strftime('%b %d, %Y at %I:%M %p'),
                'guests': booking.guests,
                'advance_paid': float(booking.advance_paid) if booking.advance_paid else 0,
                'status': booking.status,
                'status_display': booking.get_status_display(),
                'special_request': booking.special_request or '',
                'created_at': booking.created_at.strftime('%b %d, %Y %I:%M %p') if booking.created_at else '',
                'has_ac': booking.table.has_ac,
                'has_view': booking.table.has_view,
                'has_music': booking.table.has_music,
                'smoking_allowed': booking.table.smoking_allowed,
            }
        else:
            return JsonResponse({'success': False, 'error': 'Invalid booking type'}, status=400)
        
        return JsonResponse(data)
        
    except Exception as e:
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
