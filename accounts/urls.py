from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('', views.index, name='index'),
    path('register/traveller/', views.traveller_register, name='traveller_register'),
    path('register/agency/', views.agency_register, name='agency_register'),
    path('register/restaurant/', views.restaurant_register, name='restaurant_register'),
]
