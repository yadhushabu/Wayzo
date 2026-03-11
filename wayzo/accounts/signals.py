from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def set_user_verification_status(sender, instance, created, **kwargs):
    if not created:
        return

    # AUTO-VERIFY TRAVELLERS
    if instance.role == 'traveller':
        instance.is_verified = True
        instance.save(update_fields=['is_verified'])

    # AGENCY NEEDS ADMIN APPROVAL
    elif instance.role == 'agency':
        instance.is_verified = False

    # RESTAURANT NEEDS ADMIN APPROVAL
    elif instance.role == 'restaurant':
        instance.is_verified = False
