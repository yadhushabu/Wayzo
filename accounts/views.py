from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages

from .forms import (
    TravellerSignUpForm,
    AgencySignUpForm,
    RestaurantSignUpForm
)

def index(request):
    return render(request, 'accounts/index.html')


from django.contrib.auth import authenticate, login
from django.shortcuts import redirect, render
from django.contrib import messages


def login_view(request):
    if request.method == "POST":
        user = authenticate(
            request,
            username=request.POST.get("username"),
            password=request.POST.get("password")
        )

        if user:
            login(request, user)

            # Return user to the page they originally requested
            next_url = request.POST.get("next")
            if next_url:
                return redirect(next_url)

            # Admins
            if user.role == "admin" or user.is_superuser:
                return redirect("admin_app:admin_dashboard")

            # Verification check
            if not user.is_verified:
                return redirect("agency:pending_verification")

            # Role dashboards
            if user.role == "traveller":
                return redirect("travellers:dashboard")

            elif user.role == "agency":
                return redirect("agency:agency_dashboard")

            elif user.role == "restaurant":
                return redirect("restaurant_dashboard")

            # Fallback
            return redirect("travellers:dashboard")

        messages.error(request, "Invalid credentials")

    return render(request, "accounts/login.html", {
        "next": request.GET.get("next", "")
    })

def logout_view(request):
    logout(request)
    return redirect('login')


def traveller_register(request):
    if request.method == 'POST':
        form = TravellerSignUpForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = TravellerSignUpForm()

    return render(request, 'accounts/traveller_register.html', {'form': form})


def agency_register(request):
    form = AgencySignUpForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        form.save()
        return redirect('login')
    return render(request, 'accounts/agency_register.html', {'form': form})


def restaurant_register(request):
    if request.method == "POST":
        form = RestaurantSignUpForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Registration successful. Please login.")
            return redirect('login')   # ✅ ADD THIS
    else:
        form = RestaurantSignUpForm()

    return render(request, "accounts/restaurant_register.html", {"form": form})