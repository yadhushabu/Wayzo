from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('traveller', 'Traveller'),
        ('agency', 'Agency'),
        ('restaurant', 'Restaurant'),
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    is_verified = models.BooleanField(default=False)
    email = models.EmailField(unique=True)
    profile_picture = models.ImageField(
    upload_to='profile_pics/'
)

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    def get_display_name(self):
        if self.role == 'traveller':
            full_name = f"{self.first_name} {self.last_name}".strip()
            return full_name if full_name else self.username

        elif self.role == 'agency' and hasattr(self, 'agency_profile'):
            return self.agency_profile.agency_name

        elif self.role == 'restaurant' and hasattr(self, 'restaurantprofile'):
            return self.restaurantprofile.restaurant_name

        return self.username
    
    def get_phone(self):
        if hasattr(self, 'travellerprofile'):
            return self.travellerprofile.mobile

        if hasattr(self, 'agencyprofile'):
            return self.agencyprofile.mobile

        if hasattr(self, 'restaurantprofile'):
            return self.restaurantprofile.mobile

        return None