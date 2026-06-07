from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings

from admin_app.utils import create_audit_log

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def set_user_verification_status(sender, instance, created, **kwargs):

    if not created:
        return

    # ==================================================
    # USER VERIFICATION LOGIC
    # ==================================================

    # AUTO-VERIFY TRAVELLERS
    if instance.role == 'traveller':

        instance.is_verified = True
        instance.save(update_fields=['is_verified'])

    # AGENCY NEEDS ADMIN APPROVAL
    elif instance.role == 'agency':

        instance.is_verified = False
        instance.save(update_fields=['is_verified'])

    # RESTAURANT NEEDS ADMIN APPROVAL
    elif instance.role == 'restaurant':

        instance.is_verified = False
        instance.save(update_fields=['is_verified'])

    # ==================================================
    # AUDIT LOG
    # ==================================================

    create_audit_log(
        user=instance,
        action='register',
        description=f'{instance.get_display_name()} registered as {instance.role}'
    )