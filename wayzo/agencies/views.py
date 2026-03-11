from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

@login_required
def agency_dashboard(request):

    agency = request.user.agencyprofile

    return render(request, "agencies/dashboard.html", {
        "agency": agency
    })


@login_required
def pending_verification(request):
    return render(request, 'common/pending.html')
