# community/context_processors.py

from .models import Notification

def notification_counts(request):

    if request.user.is_authenticated:

        return {
            "notification_count":
                Notification.objects.filter(
                    user=request.user,
                    is_read=False
                ).count()
        }

    return {
        "notification_count": 0
    }