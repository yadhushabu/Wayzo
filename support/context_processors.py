# support/context_processors.py

from .models import Complaint

def complaint_counts(request):

    if (
        request.user.is_authenticated
        and (
            request.user.is_superuser
            or request.user.role == "admin"
        )
    ):

        return {
            "complaints_count":
                Complaint.objects.filter(
                    status="open"
                ).count()
        }

    return {
        "complaints_count": 0
    }