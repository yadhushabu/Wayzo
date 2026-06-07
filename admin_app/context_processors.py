from support.models import Complaint

def admin_notifications(request):
    if request.user.is_authenticated:
        return {
            "complaints_count": Complaint.objects.filter(
                status="open"
            ).count()
        }

    return {
        "complaints_count": 0
    }