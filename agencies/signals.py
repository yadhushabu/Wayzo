from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import AgencyProfile


@receiver(post_save, sender=AgencyProfile)
def approve_agency_user(sender, instance, **kwargs):
    if instance.is_approved:
        user = instance.user
        if not user.is_verified:
            user.is_verified = True
            user.save(update_fields=['is_verified'])
