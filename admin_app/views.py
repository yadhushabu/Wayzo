from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q, Count, F, Sum
from accounts.models import CustomUser
from admin_app.models import AuditLog
from django.core.paginator import Paginator
from support.models import Complaint


from agencies.models import AgencyProfile, PackageBooking, TourPackage
from restaurants.models import RestaurantProfile, Room, Table

from .utils import create_admin_action, create_audit_log

from destinations.models import (
    Destination,
    DestinationPlace
)


from restaurants.models import (
    RoomBooking,
    TableBooking
)
from destinations.models import DestinationPlace

User = get_user_model()

@login_required
def admin_dashboard(request):

    if request.user.role != "admin" and not request.user.is_superuser:
        messages.error(
            request,
            "You don't have permission."
        )
        return redirect("login")

    # =====================================
    # USER COUNTS
    # =====================================

    travellers_count = CustomUser.objects.filter(
        role="traveller"
    ).count()

    agencies_count = CustomUser.objects.filter(
        role="agency"
    ).count()

    restaurants_count = CustomUser.objects.filter(
        role="restaurant"
    ).count()
    
    total_users = travellers_count + agencies_count + restaurants_count
    
    active_users = CustomUser.objects.filter(
        role__in=["traveller", "agency", "restaurant"],
        is_active=True
    ).count()
    
    inactive_users = CustomUser.objects.filter(
        role__in=["traveller", "agency", "restaurant"],
        is_active=False
    ).count()
    
    # Last 7 days new users
    last_week = timezone.now() - timedelta(days=7)
    new_users = CustomUser.objects.filter(
        role__in=["traveller", "agency", "restaurant"],
        date_joined__gte=last_week
    ).count()

    # =====================================
    # VERIFICATION
    # =====================================

    verified_count = CustomUser.objects.filter(
        is_verified=True,
        role__in=["agency", "restaurant"]
    ).count()

    unverified_count = CustomUser.objects.filter(
        is_verified=False,
        role__in=["agency", "restaurant"]
    ).count()

    # =====================================
    # ACTIVE / INACTIVE
    # =====================================

    active_count = CustomUser.objects.filter(
        is_active=True
    ).count()

    inactive_count = CustomUser.objects.filter(
        is_active=False
    ).count()

    # =====================================
    # BOOKINGS
    # =====================================

    total_bookings = (
        PackageBooking.objects.count()
        + RoomBooking.objects.count()
        + TableBooking.objects.count()
    )

    # =====================================
    # APPROVALS
    # =====================================

    pending_destinations = Destination.objects.filter(
        is_approved=False
    ).count()

    pending_places = DestinationPlace.objects.filter(
        is_approved=False
    ).count()

    pending_agencies = AgencyProfile.objects.filter(
        is_approved=False
    ).count()

    pending_restaurants = RestaurantProfile.objects.filter(
        is_approved=False
    ).count()
    
    # =====================================
    # COMPLAINTS
    # =====================================

    total_destinations = Destination.objects.count()

    total_places = DestinationPlace.objects.count()

    audit_log_count = AuditLog.objects.count()

    total_complaints = Complaint.objects.count()

    open_complaints = Complaint.objects.filter(
        status="open"
    ).count()

    resolved_complaints = Complaint.objects.filter(
        status="resolved"
    ).count()
    
    # =====================================
    # RECENT ACTIVITY
    # =====================================

    recent_logs = AuditLog.objects.select_related(
        "user"
    ).order_by(
        "-created_at"
    )[:20]
    
    # =====================================
    # USERS FOR TABLE (Add this)
    # =====================================
    # Get all users for the table display
    users = CustomUser.objects.filter(
        role__in=["traveller", "agency", "restaurant"]
    ).order_by("-date_joined")[:50]  # Limit to 50 most recent for dashboard

    context = {

        # counts
        "travellers_count": travellers_count,
        "agencies_count": agencies_count,
        "restaurants_count": restaurants_count,
        
        "total_users": total_users,
        "active_users": active_users,
        "inactive_users": inactive_users,
        "new_users": new_users,

        "verified_count": verified_count,
        "unverified_count": unverified_count,

        "active_count": active_count,
        "inactive_count": inactive_count,

        "total_bookings": total_bookings,

        "pending_destinations": pending_destinations,
        "pending_places": pending_places,
        "pending_agencies": pending_agencies,
        "pending_restaurants": pending_restaurants,

        "total_destinations": total_destinations,
        "total_places": total_places,
        "audit_log_count": audit_log_count,
        
        # activity
        "recent_logs": recent_logs,
        
        # Add users for the table
        "users": users,
    }

    return render(
        request,
        "admin_app/dashboard.html",
        context
    )

def get_user_booking_count(user):

    package_count = PackageBooking.objects.filter(
        traveller=user
    ).count()

    room_count = RoomBooking.objects.filter(
        user=user
    ).count()

    table_count = TableBooking.objects.filter(
        user=user
    ).count()

    return package_count + room_count + table_count


@login_required
def user_management(request):

    if request.user.role != "admin" and not request.user.is_superuser:
        messages.error(request, "Access denied.")
        return redirect("login")

    users = User.objects.filter(
        role__in=[
            "traveller",
            "agency",
            "restaurant"
        ]
    ).order_by("-date_joined")

    # ==========================
    # GET COUNTS BEFORE FILTERING
    # ==========================
    travellers_count = User.objects.filter(role="traveller").count()
    agencies_count = User.objects.filter(role="agency").count()
    restaurants_count = User.objects.filter(role="restaurant").count()
    total_users_count = travellers_count + agencies_count + restaurants_count

    # ==========================
    # FILTER VALUES
    # ==========================

    role = request.GET.get("role")
    verification = request.GET.get("verification")
    status = request.GET.get("status")
    search = request.GET.get("search")

    bookings_filter = request.GET.get("bookings")
    audit_filter = request.GET.get("audit")

    # ==========================
    # ROLE
    # ==========================

    if role:
        users = users.filter(role=role)

    # ==========================
    # VERIFICATION
    # ==========================

    if verification == "verified":
        users = users.filter(is_verified=True)

    elif verification == "unverified":
        users = users.filter(is_verified=False)

    # ==========================
    # ACTIVE STATUS
    # ==========================

    if status == "active":
        users = users.filter(is_active=True)

    elif status == "inactive":
        users = users.filter(is_active=False)

    # ==========================
    # SEARCH
    # ==========================

    if search:

        users = users.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )

    # ==========================
    # EXTRA STATS
    # ==========================

    user_list = []

    for user in users:

        total_bookings = get_user_booking_count(user)

        audit_logs_count = AuditLog.objects.filter(
            user=user
        ).count()

        # Booking filter

        if bookings_filter == "has_bookings" and total_bookings == 0:
            continue

        if bookings_filter == "no_bookings" and total_bookings > 0:
            continue

        # Audit filter

        if audit_filter == "has_logs" and audit_logs_count == 0:
            continue

        if audit_filter == "no_logs" and audit_logs_count > 0:
            continue

        user.total_bookings = total_bookings
        user.audit_logs_count = audit_logs_count

        user_list.append(user)

    # ==========================
    # PAGINATION
    # ==========================

    paginator = Paginator(user_list, 20)

    page_number = request.GET.get("page")

    users = paginator.get_page(page_number)

    context = {

        "users": users,

        "selected_role": role,
        "selected_verification": verification,
        "selected_status": status,

        "selected_bookings": bookings_filter,
        "selected_audit": audit_filter,

        "search": search,
        
        # ==========================
        # ADD COUNTS TO CONTEXT
        # ==========================
        "total_users_count": total_users_count,
        "travellers_count": travellers_count,
        "agencies_count": agencies_count,
        "restaurants_count": restaurants_count,
    }

    return render(
        request,
        "admin_app/user_management.html",
        context
    )

from restaurants.models import PropertyMedia

@login_required
def user_profile(request, user_id):

    if request.user.role != "admin" and not request.user.is_superuser:
        messages.error(request, "Access denied.")
        return redirect("admin_app:admin_dashboard")

    user = get_object_or_404(User, id=user_id)

    context = {
        "profile_user": user
    }

    # ==================================================
    # TRAVELLER
    # ==================================================

    if user.role == "traveller":

        destinations = Destination.objects.filter(
            created_by=user
        )

        places = DestinationPlace.objects.filter(
            created_by=user
        )

        package_bookings = PackageBooking.objects.filter(
            traveller=user
        ).select_related(
            "package"
        )

        room_bookings = RoomBooking.objects.filter(
            user=user
        ).select_related(
            "room",
            "room__room_type"
        )

        table_bookings = TableBooking.objects.filter(
            user=user
        ).select_related(
            "table"
        )

        context.update({

            "destinations": destinations,
            "places": places,

            "package_bookings": package_bookings,
            "room_bookings": room_bookings,
            "table_bookings": table_bookings,

        })

    # ==================================================
    # AGENCY
    # ==================================================

    elif user.role == "agency":

        agency = getattr(
            user,
            "agencyprofile",
            None
        )

        packages = TourPackage.objects.filter(
            agency=agency
        )

        bookings_received = PackageBooking.objects.filter(
            package__agency=agency
        ).select_related(
            "traveller",
            "package"
        )

        paid_bookings_count = bookings_received.filter(
            payment_status="paid"
        ).count()
        revenue = bookings_received.filter(
            payment_status="paid"
        ).aggregate(
            total=Sum("total_amount")
        )["total"] or 0

        context.update({

            "agency_profile": agency,

            "packages": packages,

            "bookings_received": bookings_received,

            "revenue": revenue,
            "paid_bookings_count": paid_bookings_count,

        })

    # ==================================================
    # RESTAURANT
    # ==================================================

    elif user.role == "restaurant":

        restaurant = getattr(
            user,
            "restaurantprofile",
            None
        )

        rooms = Room.objects.filter(
            room_type__restaurant=restaurant
        ).select_related(
            "room_type"
        )

        tables = Table.objects.filter(
            restaurant=restaurant
        )

        room_bookings = RoomBooking.objects.filter(
            room__room_type__restaurant=restaurant
        )

        table_bookings = TableBooking.objects.filter(
            table__restaurant=restaurant
        )

        room_revenue = room_bookings.filter(
            payment_status="paid"
        ).aggregate(
            total=Sum("total_amount")
        )["total"] or 0

        table_revenue = table_bookings.filter(
            payment_status="paid"
        ).aggregate(
            total=Sum("advance_paid")
        )["total"] or 0

        total_revenue = room_revenue + table_revenue

        gallery_images = PropertyMedia.objects.filter(
            restaurant=restaurant
        )
        
        # ========== FIXED: Use correct field names for tables ==========
        # Tables don't have 'status' field, use 'is_active' or 'is_reservable'
        total_tables = tables.count()
        available_tables = tables.filter(is_active=True, is_reservable=True).count()
        # or if you want to show tables that are currently free for booking
        # available_tables = tables.filter(is_reservable=True).count()
        
        # For rooms - check if Room model has 'status' field
        total_rooms = rooms.count()
        # If Room model has 'status' field, use it; otherwise adjust
        if hasattr(Room, 'status'):
            available_rooms = rooms.filter(status="available").count()
            booked_rooms = rooms.filter(status="booked").count()
        else:
            # If no status field, use is_active or similar
            available_rooms = rooms.filter(is_active=True).count()
            booked_rooms = total_rooms - available_rooms
        # ================================================================

        context.update({

            "restaurantprofile": restaurant,

            "rooms": rooms,
            "tables": tables,

            "room_bookings": room_bookings,
            "table_bookings": table_bookings,

            "room_revenue": room_revenue,
            "table_revenue": table_revenue,
            "total_revenue": total_revenue,

            "gallery_images": gallery_images,
            
            # ========== ADD THESE TO CONTEXT ==========
            "total_rooms": total_rooms,
            "available_rooms": available_rooms,
            "booked_rooms": booked_rooms,
            
            "total_tables": total_tables,
            "available_tables": available_tables,
            # ==========================================
        })
    return render(
        request,
        "admin_app/user_profile.html",
        context
    )




@login_required
def toggle_user_status(request, user_id):

    if request.user.role != 'admin' and not request.user.is_superuser:
        messages.error(request, "You don't have permission to modify user status.")
        return redirect('admin_app:login')

    user = get_object_or_404(User, id=user_id)

    # Prevent self-deactivation
    if user.id == request.user.id:
        messages.error(request, "You cannot change your own status.")
        return redirect('admin_app:user_profile', user_id=user.id)

    # Toggle status
    user.is_active = not user.is_active
    user.save(update_fields=['is_active'])

    # Admin action log
    create_admin_action(
        admin=request.user,
        target_user=user,
        action=f"User {'activated' if user.is_active else 'deactivated'}"
    )

    # Audit log
    create_audit_log(
        user=request.user,
        action="user_status_changed",
        description=f"{request.user.username} {'activated' if user.is_active else 'deactivated'} user {user.username}"
    )

    status = "activated" if user.is_active else "deactivated"

    messages.success(
        request,
        f"User {user.username} has been {status} successfully."
    )

    return redirect(
        'admin_app:user_profile',
        user_id=user.id
    )


from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from accounts.models import CustomUser  # adjust if needed

from .utils import create_admin_action

@login_required
def toggle_verification(request, user_id):

    if request.user.role != "admin" and not request.user.is_superuser:
        return redirect("login")

    user = get_object_or_404(User, id=user_id)

    if user.role == "agency" and hasattr(user, "agencyprofile"):

        profile = user.agencyprofile

        profile.is_approved = not profile.is_approved
        profile.save()

        user.is_verified = profile.is_approved
        user.save(update_fields=["is_verified"])

        create_admin_action(
            admin=request.user,
            target_user=user,
            action=(
                "Agency Verified"
                if profile.is_approved
                else "Agency Verification Removed"
            )
        )

    elif user.role == "restaurant" and hasattr(user, "restaurantprofile"):

        profile = user.restaurantprofile

        profile.is_approved = not profile.is_approved
        profile.save()

        user.is_verified = profile.is_approved
        user.save(update_fields=["is_verified"])

        create_admin_action(
            admin=request.user,
            target_user=user,
            action=(
                "Restaurant Verified"
                if profile.is_approved
                else "Restaurant Verification Removed"
            )
        )

    return redirect(
        "admin_app:user_profile",
        user_id=user.id
    )


from django.contrib.admin.views.decorators import staff_member_required
from destinations.models import Destination, DestinationPlace

@staff_member_required
def admin_approvals(request):
    pending_destinations = Destination.objects.filter(is_approved=False).order_by('-created_at')
    pending_places = DestinationPlace.objects.filter(is_approved=False).select_related('destination', 'created_by').order_by('-created_at')
    
    # Calculate total pending count
    pending_count = pending_destinations.count() + pending_places.count()
    
    return render(request, "admin_app/admin_approvals.html", {
        "pending_destinations": pending_destinations,
        "pending_places": pending_places,
        "pending_count": pending_count,  # Add this
    })

@login_required
def audit_logs(request):

    if request.user.role != "admin" and not request.user.is_superuser:
        messages.error(request, "Access denied.")
        return redirect("login")

    logs = AuditLog.objects.select_related(
        "user"
    ).order_by("-created_at")

    # ==========================
    # FILTERS
    # ==========================

    search = request.GET.get("search")
    action = request.GET.get("action")
    role = request.GET.get("role")
    date = request.GET.get("date")

    # Search

    if search:
        logs = logs.filter(
            Q(user__username__icontains=search) |
            Q(description__icontains=search)
        )

    # Action filter

    if action:
        logs = logs.filter(
            action=action
        )

    # Role filter

    if role:
        logs = logs.filter(
            user_role=role
        )

    # Date filter

    if date:
        logs = logs.filter(
            created_at__date=date
        )

    # ==========================
    # PAGINATION
    # ==========================

    paginator = Paginator(logs, 30)

    page_number = request.GET.get("page")

    logs = paginator.get_page(page_number)

    context = {
        "logs": logs,

        "selected_action": action,
        "selected_role": role,
        "selected_date": date,
        "search": search,

        # Dropdown values
        "actions": AuditLog.objects.values_list(
            "action",
            flat=True
        ).distinct(),

        "roles": AuditLog.objects.values_list(
            "user_role",
            flat=True
        ).distinct(),
    }

    return render(
        request,
        "admin_app/audit_logs.html",
        context
    )

import csv
from django.http import HttpResponse
from admin_app.models import AuditLog

@login_required
def audit_logs_export(request):

    if request.user.role != "admin" and not request.user.is_superuser:
        return redirect("login")

    logs = AuditLog.objects.select_related("user")

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = (
        'attachment; filename="audit_logs.csv"'
    )

    writer = csv.writer(response)

    writer.writerow([
        "User",
        "Role",
        "Action",
        "Description",
        "Date"
    ])

    for log in logs:
        writer.writerow([
            log.user.username,
            log.user_role,
            log.action,
            log.description,
            log.created_at.strftime("%Y-%m-%d %H:%M")
        ])

    return response