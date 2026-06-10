from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from .forms import AgencyProfileEditForm, CancellationPolicyFormSet, TourPackageForm, PackageItineraryForm
from .models import AgencyProfile, TourPackage, PackageItinerary, PackageBooking, PackageImage
from community.models import Notification
from community.models import Notification
from django.db.models import Count, Sum
from django.utils.timezone import now
from django.contrib.auth.decorators import login_required
from .models import AgencyProfile, TourPackage, PackageBooking
from community.models import Notification
from .utils import auto_cancel_expired_bookings

from admin_app.utils import create_audit_log

@login_required
def agency_dashboard(request):
    auto_cancel_expired_bookings()
    agency = request.user.agencyprofile

    # Get packages with booking count using the correct related name 'packagebooking'
    packages = TourPackage.objects.filter(agency=agency).prefetch_related('images')
    packages = packages.annotate(bookings_count=Count('packagebooking'))
    
    # Get all bookings
    bookings = PackageBooking.objects.filter(
        package__agency=agency
    ).select_related('package', 'traveller')

    packages_count = packages.count()
    bookings_count = bookings.count()
    
    # Calculate dashboard revenue from confirmed/completed bookings
    dashboard_revenue = PackageBooking.objects.filter(
        package__agency=agency,
        status__in=["confirmed", "completed"]
    ).aggregate(total=Sum("total_amount"))["total"] or 0

    # Upcoming bookings
    upcoming_bookings = bookings.filter(
        travel_date__gte=now().date(),
        status__in=["pending", "confirmed"]
    ).order_by('travel_date')[:5]

    # Notifications
    unread_notifications = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).count()

    test_notification = Notification.objects.create(
        user=request.user,
        notification_type='message',
        message='🔔 This is a test notification to check if the system is working!'
    )

    return render(request, "agencies/dashboard.html", {
        "agency": agency,
        "packages": packages,
        "bookings": bookings,
        "packages_count": packages_count,
        "bookings_count": bookings_count,
        "dashboard_revenue": dashboard_revenue,
        "upcoming_bookings": upcoming_bookings,
        "unread_notifications": unread_notifications,
    })

@login_required
def pending_verification(request):
    """Show pending verification page for unverified users"""
    return render(request, 'common/pending.html', {
        'user': request.user,
    })



@login_required
def edit_agencyprofile(request):
    agency = request.user.agencyprofile
    user = request.user

    if request.method == "POST":
        form = AgencyProfileEditForm(
            request.POST,
            request.FILES,
            instance=agency
        )

        profile_picture = request.FILES.get("profile_picture")

        if form.is_valid():
            form.save()

            create_audit_log(
                user=request.user,
                action='profile_updated',
                description='Updated agency profile'
            )

            if profile_picture:
                user.profile_picture = profile_picture
                user.save()
        
            messages.success(request, "Your profile has been updated successfully!")
            return redirect("agency:agency_dashboard")
        else:
            messages.error(request, "Please correct the errors below.")

    else:
        form = AgencyProfileEditForm(instance=agency)

    context = {
        "form": form,
        "user": user,
        "agency": agency,  # ✅ Add this for the base template
    }

    return render(request, "agencies/edit_profile.html", context)


from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Sum

from django.utils.timezone import now
from datetime import date

@login_required
def agency_bookings(request):

    auto_cancel_expired_bookings()

    agency = request.user.agencyprofile
    today_date = timezone.now().date()

    # ===================================
    # AUTO COMPLETE FINISHED TRIPS
    # ===================================

    active_bookings = PackageBooking.objects.filter(
        package__agency=agency,
        status="in_progress",
        payment_status="paid"
    ).select_related("package")

    for booking in active_bookings:

        if booking.trip_end_date < today_date:
            booking.complete_trip()

    # ===================================
    # FETCH BOOKINGS
    # ===================================

    bookings = PackageBooking.objects.filter(
        package__agency=agency
    ).select_related(
        "package",
        "traveller"
    ).order_by("-booked_at")

    # ===================================
    # STATS
    # ===================================

    total_bookings = bookings.count()

    pending_count = bookings.filter(
        status="pending"
    ).count()

    confirmed_count = bookings.filter(
        status="confirmed"
    ).count()

    ongoing_count = bookings.filter(
        status="in_progress"
    ).count()

    completed_count = bookings.filter(
        status="completed"
    ).count()

    # ===================================
    # DISPLAY FLAGS
    # ===================================

    for booking in bookings:

        booking.is_upcoming = (
            booking.status == "confirmed"
            and booking.travel_date > today_date
        )

        booking.is_ongoing = (
            booking.status == "in_progress"
        )

        booking.is_completed_display = (
            booking.status == "completed"
        )

    # ===================================
    # PAGINATION
    # ===================================

    paginator = Paginator(bookings, 12)

    page = request.GET.get("page", 1)

    try:
        bookings_page = paginator.page(page)

    except PageNotAnInteger:
        bookings_page = paginator.page(1)

    except EmptyPage:
        bookings_page = paginator.page(
            paginator.num_pages
        )

    context = {
        "bookings": bookings_page,
        "total_bookings": total_bookings,
        "pending_count": pending_count,
        "confirmed_count": confirmed_count,
        "ongoing_count": ongoing_count,
        "completed_count": completed_count,
        "today": today_date,
        "agency": agency,
    }

    return render(
        request,
        "agencies/bookings.html",
        context
    )

@login_required
def agency_packages(request):
    agency = request.user.agencyprofile
    packages = TourPackage.objects.filter(agency=agency).order_by('-is_featured', '-created_at')
    
    # Get filter parameters
    current_category = request.GET.get('category', 'all')
    current_sort = request.GET.get('sort', 'featured')
    
    # Apply filters based on category
    if current_category == 'featured':
        packages = packages.filter(is_featured=True)
    elif current_category == 'active':
        packages = packages.filter(is_active=True)
    elif current_category == 'inactive':
        packages = packages.filter(is_active=False)
    
    # Apply sorting
    if current_sort == 'newest':
        packages = packages.order_by('-created_at')
    elif current_sort == 'price_low':
        packages = packages.order_by('price')
    elif current_sort == 'price_high':
        packages = packages.order_by('-price')
    elif current_sort == 'name':
        packages = packages.order_by('title')
    else:  # featured
        packages = packages.order_by('-is_featured', '-created_at')
    
    # Apply price filter
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    if min_price:
        packages = packages.filter(price__gte=min_price)
    if max_price:
        packages = packages.filter(price__lte=max_price)
    
    # Apply duration filter
    duration = request.GET.get('duration')
    if duration == 'short':
        packages = packages.filter(duration_days__lte=3)
    elif duration == 'medium':
        packages = packages.filter(duration_days__gte=4, duration_days__lte=7)
    elif duration == 'long':
        packages = packages.filter(duration_days__gte=8)
    
    # Apply status filter
    status_filter = request.GET.get('status')
    if status_filter == 'active':
        packages = packages.filter(is_active=True)
    elif status_filter == 'inactive':
        packages = packages.filter(is_active=False)
    
    context = {
        "packages": packages,
        "agency": agency,  # ✅ ADD THIS - required by base template
        "user": request.user,  # ✅ ADD THIS - for profile picture
        "current_category": current_category,
        "current_sort": current_sort,
    }
    
    return render(request, "agencies/packages.html", context)

from django.shortcuts import render, redirect
from .forms import (
    TourPackageForm,
    PackageItineraryFormSet,
    PackageImageFormSet
)

from django.contrib import messages

@login_required
def add_package(request):
    agency = request.user.agencyprofile
    
    if request.method == "POST":
        package_form = TourPackageForm(request.POST)
        itinerary_formset = PackageItineraryFormSet(request.POST, prefix="itineraries")
        image_formset = PackageImageFormSet(request.POST, request.FILES, prefix="images")
        policy_formset = CancellationPolicyFormSet(request.POST, prefix="cancellation_policies")

        if package_form.is_valid() and itinerary_formset.is_valid() and image_formset.is_valid() and policy_formset.is_valid():
            try:
                package = package_form.save(commit=False)
                package.agency = agency
                package.save()

                # Save itineraries
                itineraries = itinerary_formset.save(commit=False)
                for itinerary in itineraries:
                    itinerary.package = package
                    itinerary.save()
                
                # Delete removed itineraries
                for itinerary in itinerary_formset.deleted_objects:
                    itinerary.delete()

                # Save images
                images = image_formset.save(commit=False)
                for image in images:
                    image.package = package
                    image.save()
                
                # Delete removed images
                for image in image_formset.deleted_objects:
                    image.delete()

                # Save cancellation policies
                policies = policy_formset.save(commit=False)
                for policy in policies:
                    policy.package = package
                    policy.save()
                
                # Delete removed policies
                for policy in policy_formset.deleted_objects:
                    policy.delete()

                # Create notification
                Notification.objects.create(
                    user=request.user,
                    notification_type="trip_update",
                    message=f"New package '{package.title}' added successfully"
                )

                messages.success(request, f"Package '{package.title}' has been created successfully!")
                return redirect("agency:agency_packages")
            
                create_audit_log(
                    user=request.user,
                    action='package_added',
                    description=f'Added package: {package.title}'
                )
                                
            except Exception as e:
                messages.error(request, f"Error saving package: {str(e)}")
        else:
            if not package_form.is_valid():
                messages.error(request, "Please correct the errors in the package details.")
                print("Package form errors:", package_form.errors)
            if not itinerary_formset.is_valid():
                messages.error(request, "Please correct the errors in the itinerary section.")
                print("Itinerary formset errors:", itinerary_formset.errors)
            if not image_formset.is_valid():
                messages.error(request, "Please correct the errors in the images section.")
                print("Image formset errors:", image_formset.errors)
            if not policy_formset.is_valid():
                messages.error(request, "Please correct the errors in the cancellation policy section.")
                print("Policy formset errors:", policy_formset.errors)
    else:
        package_form = TourPackageForm()
        itinerary_formset = PackageItineraryFormSet(prefix="itineraries")
        image_formset = PackageImageFormSet(prefix="images")
        policy_formset = CancellationPolicyFormSet(prefix="cancellation_policies")

    # Get notifications for the sidebar
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')[:5]
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()

    return render(request, "agencies/add_package.html", {
        "package_form": package_form,
        "itinerary_formset": itinerary_formset,
        "image_formset": image_formset,
        "policy_formset": policy_formset,
        "agency": agency,
        "notifications": notifications,
        "unread_count": unread_count,
        "user": request.user,
    })


@login_required
def edit_package(request, id):
    package = get_object_or_404(
        TourPackage,
        id=id,
        agency=request.user.agencyprofile
    )
    
    # Get the agency profile for the base template
    agency = request.user.agencyprofile

    if request.method == "POST":
        form = TourPackageForm(request.POST, request.FILES, instance=package)
        
        # IMPORTANT: Add form_kwargs to prevent validation of extra empty forms
        itinerary_formset = PackageItineraryFormSet(
            request.POST, 
            instance=package, 
            prefix="itineraries",
            form_kwargs={'empty_permitted': True}  # Allow empty forms
        )
        
        image_formset = PackageImageFormSet(
            request.POST, 
            request.FILES, 
            instance=package, 
            prefix="images",
            form_kwargs={'empty_permitted': True}  # Allow empty forms
        )

        if form.is_valid() and itinerary_formset.is_valid() and image_formset.is_valid():
            try:
                package = form.save()
                
                # Save itineraries
                itineraries = itinerary_formset.save(commit=False)
                for itinerary in itineraries:
                    itinerary.package = package
                    itinerary.save()
                
                # Delete removed itineraries
                for itinerary in itinerary_formset.deleted_objects:
                    itinerary.delete()
                
                # Save images
                images = image_formset.save(commit=False)
                for image in images:
                    image.package = package
                    image.save()
                
                # Delete removed images
                for image in image_formset.deleted_objects:
                    image.delete()
                
                messages.success(request, f"Package '{package.title}' has been updated successfully!")
                return redirect('agency:package_detail', id=package.id)
            
                create_audit_log(
                    user=request.user,
                    action='package_updated',
                    description=f'Updated package: {package.title}'
                )
                
            except Exception as e:
                print(f"Error saving package: {e}")
                messages.error(request, f"Error saving package: {str(e)}")
        else:
            if not form.is_valid():
                messages.error(request, "Please correct the errors in the package details.")
                print("Form errors:", form.errors)
            if not itinerary_formset.is_valid():
                messages.error(request, "Please correct the errors in the itinerary section.")
                print("Itinerary formset errors:", itinerary_formset.errors)
            if not image_formset.is_valid():
                messages.error(request, "Please correct the errors in the images section.")
                print("Image formset errors:", image_formset.errors)

    else:
        form = TourPackageForm(instance=package)
        itinerary_formset = PackageItineraryFormSet(instance=package, prefix="itineraries")
        image_formset = PackageImageFormSet(instance=package, prefix="images")

    context = {
        "form": form,
        "itinerary_formset": itinerary_formset,
        "image_formset": image_formset,
        "package": package,
        "agency": agency,  # ✅ ADD THIS - required by base template
        "user": request.user,  # ✅ ADD THIS - for profile picture
    }

    return render(request, "agencies/edit_package.html", context)

@login_required
def delete_package(request, id):
    package = get_object_or_404(
        TourPackage,
        id=id,
        agency=request.user.agencyprofile
    )
    package_title = package.title
    create_audit_log(
        user=request.user,
        action='package_deleted',
        description=f'Deleted package: {package_title}'
    )

    package.delete()

    
    return redirect('agency:agency_packages')

from django.shortcuts import render, get_object_or_404

def package_detail(request, id):
    package = get_object_or_404(TourPackage, id=id)

    # check if agency owner
    is_owner = False
    agency = None
    
    if request.user.is_authenticated and hasattr(request.user, "agencyprofile"):
        agency = request.user.agencyprofile
        is_owner = package.agency == agency

    # fetch related data
    itineraries = package.itineraries.all()
    images = package.images.all()

    return render(request, "agencies/package_detail.html", {
        "package": package,
        "is_owner": is_owner,
        "itineraries": itineraries,
        "images": images,
        "agency": agency,  # ✅ ADD THIS - required by base template
        "user": request.user,  # ✅ ADD THIS - for profile picture
    })


def agency_detail(request, id):
    agency = get_object_or_404(AgencyProfile, id=id, is_approved=True)

    packages = agency.packages.all().prefetch_related("images")

    return render(request, "travellers/agency_detail.html", {
        "agency": agency,
        "packages": packages
    })

@login_required
def approve_booking(request, id):
    booking = get_object_or_404(
        PackageBooking,
        id=id,
        package__agency=request.user.agencyprofile
    )

    booking.status = "confirmed"
    booking.save()

    create_audit_log(
        user=request.user,
        action='booking_approved',
        description=f'Approved booking #{booking.id} for {booking.package.title}'
    )

    # 🔔 notify traveller
    Notification.objects.create(
        user=booking.traveller,
        message=f"Your booking for {booking.package.title} is CONFIRMED!",
        notification_type="booking"
    )

    return redirect("agency:agency_bookings")


from django.utils import timezone
from agencies.models import Refund  # adjust import if needed

from django.utils import timezone
from agencies.models import Refund
from community.models import Notification
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from agencies.utils import process_refund


@login_required
def reject_booking(request, id):
    booking = get_object_or_404(
        PackageBooking,
        id=id,
        package__agency=request.user.agencyprofile
    )

    # ❌ Prevent double processing
    if booking.status == "rejected":
        return redirect("agency:agency_bookings")

    # =========================
    # 1. UPDATE BOOKING STATE
    # =========================
    booking.status = "rejected"
    booking.cancelled_by = "agency"
    booking.refund_amount = booking.total_amount or 0
    booking.refund_status = "processing"
    booking.save()

    create_audit_log(
        user=request.user,
        action='booking_rejected',
        description=f'Rejected booking #{booking.id} for {booking.package.title}'
    )

    # =========================
    # 2. PROCESS REFUND (single source of truth)
    # =========================
    refund = process_refund(booking)

    # =========================
    # 3. NOTIFICATION
    # =========================
    Notification.objects.create(
        user=booking.traveller,
        sender=request.user,
        notification_type="refund",
        message=(
            f"❌ Your booking for {booking.package.title} was rejected. "
            f"Refund of ₹{refund.amount} has been credited successfully."
        )
    )

    return redirect("agency:agency_bookings")


@login_required
def cancel_booking_by_agency(request, id):
    booking = get_object_or_404(
        PackageBooking,
        id=id,
        package__agency=request.user.agencyprofile
    )

    if booking.status == "confirmed":
        booking.status = "cancelled"
        booking.cancelled_by = "agency"

        refund_amount = booking.total_amount or 0

        booking.refund_amount = refund_amount
        booking.refund_percentage = 100
        booking.save()

        create_audit_log(
            user=request.user,
            action='booking_cancelled',
            description=f'Cancelled booking #{booking.id} for {booking.package.title}'
        )

        Notification.objects.create(
            user=booking.traveller,
            message=f"⚠️ Your booking for {booking.package.title} was cancelled by agency. Full refund ₹{refund_amount}",
            notification_type="booking"
        )

    return redirect("agency:agency_bookings")


from django.db.models import Sum, Count
from django.db.models.functions import TruncMonth
from django.contrib.auth.decorators import login_required

@login_required
def agency_earnings(request):
    auto_cancel_expired_bookings()
    
    agency = request.user.agencyprofile
    
    # Debug: Print to console
    print(f"Agency: {agency.agency_name}")
    print(f"Agency ID: {agency.id}")

    bookings = PackageBooking.objects.filter(
        package__agency=agency,
        status__in=["confirmed", "completed"]
    )
    
    print(f"Total bookings found: {bookings.count()}")
    for b in bookings:
        print(f"  - {b.package.title}: ₹{b.total_amount}")

    total_earnings = bookings.aggregate(
        total=Sum("total_amount")
    )["total"] or 0

    total_bookings = bookings.count()

    pending_payments = PackageBooking.objects.filter(
        package__agency=agency,
        payment_status="partial"
    ).aggregate(
        total=Sum("remaining_amount")
    )["total"] or 0

    cancelled_bookings = PackageBooking.objects.filter(
        package__agency=agency,
        status="cancelled"
    ).count()

    package_revenue = list(
        bookings.values("package__title")
        .annotate(revenue=Sum("total_amount"))
        .order_by("-revenue")
    )
    
    print(f"Package revenue data: {package_revenue}")

    monthly_revenue = list(
        bookings.annotate(month=TruncMonth("booked_at"))
        .values("month")
        .annotate(total=Sum("total_amount"))
        .order_by("month")
    )
    
    print(f"Monthly revenue data: {monthly_revenue}")

    top_packages = list(
        bookings.values("package__title")
        .annotate(
            revenue=Sum("total_amount"),
            bookings_count=Count("id")
        )
        .order_by("-revenue")[:5]
    )

    context = {
        "agency": agency,
        "total_earnings": total_earnings,
        "total_bookings": total_bookings,
        "pending_payments": pending_payments,
        "cancelled_bookings": cancelled_bookings,
        "package_revenue": package_revenue,
        "monthly_revenue": monthly_revenue,
        "top_packages": top_packages,
        "recent_bookings": bookings.order_by("-booked_at")[:10],
    }

    return render(
        request,
        "agencies/earnings.html",
        context
    )

from django.http import JsonResponse
from django.utils.timezone import now
from datetime import date

@login_required
def booking_details_api(request, booking_id):
    """API endpoint to get booking details for modal"""
    try:
        booking = PackageBooking.objects.select_related('package', 'traveller').get(
            id=booking_id,
            package__agency=request.user.agencyprofile
        )
        
        today_date = date.today()
        
        data = {
            'id': booking.id,
            'package_title': booking.package.title,
            'traveller_name': booking.traveller.get_full_name() or booking.traveller.username,
            'traveller_email': booking.traveller.email,
            'traveller_phone': getattr(booking.traveller, 'phone', None) or 'Not provided',
            'travel_date': booking.travel_date.strftime('%d %b %Y'),
            'travellers_count': booking.travellers_count,
            'total_amount': str(booking.total_amount),
            'advance_amount': str(booking.advance_amount) if booking.advance_amount else '0',
            'remaining_amount': str(booking.remaining_amount) if booking.remaining_amount else str(booking.total_amount),
            'payment_status': booking.payment_status,
            'status': booking.status,
            'booked_at': booking.booked_at.strftime('%d %b %Y, %I:%M %p'),
            'is_upcoming': booking.travel_date > today_date,
            'is_ongoing': booking.travel_date == today_date,
            'is_completed': booking.travel_date < today_date and booking.status == 'confirmed',
            'cancelled_by': booking.cancelled_by,
            'refund_amount': str(booking.refund_amount) if booking.refund_amount else '0',
            'refund_status': booking.refund_status,
        }
        
        return JsonResponse(data)
    except PackageBooking.DoesNotExist:
        return JsonResponse({'error': 'Booking not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    

@login_required
def mark_package_completed(request, booking_id):

    booking = get_object_or_404(
        PackageBooking,
        id=booking_id,
        package__agency__user=request.user
    )

    if booking.can_mark_completed:

        booking.complete_trip()

        # Traveller notification
        Notification.objects.create(
            user=booking.traveller,
            notification_type="booking",
            message=f"Your trip '{booking.package.title}' has been marked as completed."
        )

        # Agency notification
        Notification.objects.create(
            user=booking.package.agency.user,
            notification_type="booking",
            message=f"Trip completed for {booking.package.title}"
        )

    return redirect("agencies:package_bookings")