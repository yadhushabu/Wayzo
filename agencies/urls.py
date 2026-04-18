from django.urls import path
from . import views
app_name = "agency"

urlpatterns = [
    path('dashboard/', views.agency_dashboard, name='agency_dashboard'),
    path('pending/', views.pending_verification, name='pending_verification'),
    path("edit-profile/", views.edit_agencyprofile, name="edit_agencyprofile"),
    path("bookings/", views.agency_bookings, name="agency_bookings"),
    path("packages/", views.agency_packages, name="agency_packages"),
    path('packages/add/', views.add_package, name='add_package'),
    path('packages/edit/<int:id>/', views.edit_package, name='edit_package'),
    path('packages/delete/<int:id>/', views.delete_package, name='delete_package'),
    path('package/<int:id>/', views.package_detail, name='package_detail'),
    path('agency/<int:id>/', views.agency_detail, name='agency_detail'),
    path('booking/approve/<int:id>/', views.approve_booking, name='approve_booking'),
    path('booking/reject/<int:id>/', views.reject_booking, name='reject_booking'),
    path('notifications/', views.all_notifications, name='all_notifications'),
    path('cancel_booking/<int:id>/',views.cancel_booking_by_agency,name="cancel_booking_by_agency")

]
