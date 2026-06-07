# admin_app/utils.py

from .models import AuditLog


def create_audit_log(user, action, description):

    AuditLog.objects.create(
        user=user,
        user_role=user.role,
        action=action,
        description=description
    )

from .models import AdminActionLog


def create_admin_action(
    admin,
    target_user,
    action
):

    AdminActionLog.objects.create(
        admin=admin,
        target_user=target_user,
        action=action
    )