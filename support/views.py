from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages

from .models import Complaint
from .forms import ComplaintForm

from django.contrib.auth import get_user_model
from community.models import Notification

User = get_user_model()

from admin_app.utils import create_audit_log


@login_required
def support_center(request):

    if request.method == "POST":

        form = ComplaintForm(
            request.POST,
            request.FILES
        )

        if form.is_valid():

            complaint = form.save(
                commit=False
            )

            complaint.user = request.user

            complaint.save()

            admins = User.objects.filter(
                is_superuser=True
            )

            for admin in admins:

                Notification.create_complaint_created_notification(
                    complaint=complaint,
                    admin_user=admin
                )

            create_audit_log(
                user=request.user,
                action="complaint_created",
                description=f"Submitted complaint: {complaint.title}"
            )

            messages.success(
                request,
                "Complaint submitted successfully."
            )

            return redirect(
                "support:support_center"
            )

    else:

        form = ComplaintForm()

    complaints = Complaint.objects.filter(
        user=request.user
    )

    context = {
        "form": form,
        "complaints": complaints,
    }

    # ======================================
    # AGENCY
    # ======================================

    if request.user.role == "agency":

        context["base_template"] = (
            "agencies/base_agencies.html"
        )

        if hasattr(request.user, "agencyprofile"):
            context["agency"] = (
                request.user.agencyprofile
            )

    # ======================================
    # RESTAURANT
    # ======================================

    elif request.user.role == "restaurant":

        context["base_template"] = (
            "restaurants/base_restaurant.html"
        )

        if hasattr(request.user, "restaurantprofile"):
            context["restaurant"] = (
                request.user.restaurantprofile
            )

    # ======================================
    # TRAVELLER
    # ======================================

    else:

        context["base_template"] = (
            "travellers/base.html"
        )

        if hasattr(request.user, "travellerprofile"):
            context["traveller"] = (
                request.user.travellerprofile
            )

    return render(
        request,
        "support/support_center.html",
        context
    )


@login_required
def complaint_detail(request, complaint_id):

    complaint = Complaint.objects.get(
        id=complaint_id,
        user=request.user
    )

    context = {
        "complaint": complaint
    }

    # ======================================
    # AGENCY
    # ======================================

    if request.user.role == "agency":

        context["base_template"] = (
            "agencies/base_agencies.html"
        )

        if hasattr(request.user, "agencyprofile"):
            context["agency"] = (
                request.user.agencyprofile
            )

    # ======================================
    # RESTAURANT
    # ======================================

    elif request.user.role == "restaurant":

        context["base_template"] = (
            "restaurants/base_restaurant.html"
        )

        if hasattr(request.user, "restaurantprofile"):
            context["restaurant"] = (
                request.user.restaurantprofile
            )

    # ======================================
    # TRAVELLER
    # ======================================

    else:

        context["base_template"] = (
            "travellers/base.html"
        )

        if hasattr(request.user, "travellerprofile"):
            context["traveller"] = (
                request.user.travellerprofile
            )

    return render(
        request,
        "support/complaint_detail.html",
        context
    )

from django.contrib.auth import get_user_model

User = get_user_model()


@login_required
def admin_complaints(request):

    if (
        request.user.role != "admin"
        and not request.user.is_superuser
    ):
        return redirect("login")

    complaints = Complaint.objects.select_related("user")

    status = request.GET.get("status")
    user_type = request.GET.get("role")
    search = request.GET.get("search")

    if status:
        complaints = complaints.filter(status=status)

    if user_type:
        complaints = complaints.filter(user__role=user_type)

    if search:
        complaints = complaints.filter(user__username__icontains=search) | \
                     complaints.filter(title__icontains=search)

    stats = {
        "total":       Complaint.objects.count(),
        "open":        Complaint.objects.filter(status="open").count(),
        "in_progress": Complaint.objects.filter(status="in_progress").count(),
        "resolved":    Complaint.objects.filter(status="resolved").count(),
        "closed":      Complaint.objects.filter(status="closed").count(),
    }

    return render(
        request,
        "support/admin_complaints.html",
        {
            "complaints": complaints,
            "stats": stats,      
        }
    )

@login_required
def complaint_detail_admin(request, complaint_id):

    if request.user.role != "admin" and not request.user.is_superuser:
        return redirect("login")

    complaint = Complaint.objects.select_related("user").get(id=complaint_id)

    return render(request, "support/admin_complaint_detail.html", {
        "complaint": complaint
    })


@login_required
def update_complaint(request, complaint_id):

    if (
        request.user.role != "admin"
        and not request.user.is_superuser
    ):
        return redirect("login")

    complaint = Complaint.objects.get(
        id=complaint_id
    )

    if request.method == "POST":

        old_status = complaint.status

        complaint.status = request.POST.get(
            "status"
        )

        complaint.admin_response = request.POST.get(
            "admin_response"
        )

        complaint.save()

        if complaint.admin_response:

            Notification.create_complaint_response_notification(
                complaint=complaint,
                admin_user=request.user
            )

        if (
            old_status != "resolved"
            and complaint.status == "resolved"
        ):

            Notification.create_complaint_resolved_notification(
                complaint=complaint,
                admin_user=request.user
            )

        create_audit_log(
            user=request.user,
            action="complaint_updated",
            description=f"Updated complaint #{complaint.id}"
        )

        messages.success(
            request,
            "Complaint updated successfully."
        )

    return redirect(
        "support:admin_complaints"
    )