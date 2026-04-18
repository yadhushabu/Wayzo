from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from .forms import AgencyProfileEditForm, CancellationPolicyFormSet, TourPackageForm, PackageItineraryForm
from .models import AgencyProfile, TourPackage, PackageItinerary, PackageBooking, PackageImage
from community.models import Notification

from django.utils.timezone import now
from django.contrib.auth.decorators import login_required

@login_required
def agency_dashboard(request):
    agency = request.user.agencyprofile

    packages = TourPackage.objects.filter(agency=agency)

    bookings = PackageBooking.objects.filter(
        package__agency=agency
    ).select_related('package', 'traveller')

    packages_count = packages.count()
    bookings_count = bookings.count()

    # ✅ Upcoming bookings (important part)
    upcoming_bookings = bookings.filter(
        travel_date__gte=now().date(),
        status__in=["pending", "confirmed"]
    ).order_by('travel_date')[:5]

    # 🔔 Notifications
    unread_notifications = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).count()

    return render(request, "agencies/dashboard.html", {
        "agency": agency,
        "packages": packages,
        "bookings": bookings,
        "packages_count": packages_count,
        "bookings_count": bookings_count,
        "upcoming_bookings": upcoming_bookings,   # 👈 NEW
        "unread_notifications": unread_notifications,
    })


@login_required
def pending_verification(request):
    return render(request, 'common/pending.html')



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

            if profile_picture:
                user.profile_picture = profile_picture
                user.save()

            return redirect("agency:agency_dashboard")

    else:
        form = AgencyProfileEditForm(instance=agency)

    return render(
        request,
        "agencies/edit_profile.html",
        {
            "form": form,
            "user": user
        }
    )

def agency_bookings(request):
    bookings = PackageBooking.objects.select_related(
        'package',
        'traveller'
    )

    return render(request, 'agencies/bookings.html', {
        'bookings': bookings
    })

@login_required
def agency_packages(request):

    agency = request.user.agencyprofile

    packages = TourPackage.objects.filter(agency=agency).order_by('-is_featured', '-created_at')

    return render(request,"agencies/packages.html",{
        "packages":packages
    })

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
                
            except Exception as e:
                print(f"Error saving package: {e}")
                messages.error(request, f"Error saving package: {str(e)}")
        else:
            if not form.is_valid():
                messages.error(request, "Please correct the errors in the package details.")
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

    return render(request, "agencies/edit_package.html", {
        "form": form,
        "itinerary_formset": itinerary_formset,
        "image_formset": image_formset,
        "package": package
    })

@login_required
def delete_package(request, id):
    package = get_object_or_404(
        TourPackage,
        id=id,
        agency=request.user.agencyprofile
    )

    package.delete()
    return redirect('agency:agency_packages')

from django.shortcuts import render, get_object_or_404

def package_detail(request, id):
    package = get_object_or_404(TourPackage, id=id)

    # check if agency owner
    is_owner = False
    if request.user.is_authenticated and hasattr(request.user, "agencyprofile"):
        is_owner = package.agency == request.user.agencyprofile

    # ✅ fetch related data
    itineraries = package.itineraries.all()
    images = package.images.all()

    return render(request, "agencies/package_detail.html", {
        "package": package,
        "is_owner": is_owner,
        "itineraries": itineraries,
        "images": images,
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

    # 🔔 notify traveller
    Notification.objects.create(
        user=booking.traveller,
        message=f"Your booking for {booking.package.title} is CONFIRMED!",
        notification_type="booking"
    )

    return redirect("agency:agency_bookings")


@login_required
def reject_booking(request, id):
    booking = get_object_or_404(
        PackageBooking,
        id=id,
        package__agency=request.user.agencyprofile
    )

    booking.status = "rejected"
    booking.cancelled_by = "agency"
    booking.save()

    # FULL REFUND
    refund_amount = booking.total_amount or 0

    Notification.objects.create(
        user=booking.traveller,
        message=f"❌ Your booking for {booking.package.title} was rejected. Full refund ₹{refund_amount}",
        notification_type="booking"
    )

    return redirect("agency:agency_bookings")

@login_required
def all_notifications(request):
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')

    return render(request, "notifications/all_notifications.html", {
        "notifications": notifications
    })


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

        Notification.objects.create(
            user=booking.traveller,
            message=f"⚠️ Your booking for {booking.package.title} was cancelled by agency. Full refund ₹{refund_amount}",
            notification_type="booking"
        )

    return redirect("agency:agency_bookings")