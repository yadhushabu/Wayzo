from django.urls import path
from . import views

app_name = "support"

urlpatterns = [

    path(
        "",
        views.support_center,
        name="support_center"
    ),

    path(
        "complaint/<int:complaint_id>/",
        views.complaint_detail,
        name="complaint_detail"
    ),

    path(
        "admin/",
        views.admin_complaints,
        name="admin_complaints"
    ),

    path(
        "update/<int:complaint_id>/",
        views.update_complaint,
        name="update_complaint"
    ),
    path("admin/complaints/<int:complaint_id>/", views.complaint_detail_admin, name="complaint_detail_admin"),

]