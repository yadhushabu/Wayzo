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


def login_view(request):
    if request.method == "POST":
        user = authenticate(
            request,
            username=request.POST['username'],
            password=request.POST['password']
        )

        if user:

            # 🔥 Login first
            login(request, user)

            # 🔥 If admin → go directly to admin dashboard
            if user.role == 'admin' or user.is_superuser:
                return redirect('admin_app:admin_dashboard')  

            # 🔥 Only normal users need verification
            if not user.is_verified:
                return redirect('agency:pending_verification')

            # 🔥 Role-based dashboards
            if user.role == 'traveller':
                return redirect('travellers:dashboard')
            elif user.role == 'agency':
                return redirect('agency:agency_dashboard')
            elif user.role == 'restaurant':
                return redirect('restaurant_dashboard')

        else:
            messages.error(request, "Invalid credentials")

    return render(request, 'accounts/login.html')

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