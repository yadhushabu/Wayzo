# admin_app/models.py

from django.db import models
from django.conf import settings


class AuditLog(models.Model):

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    user_role = models.CharField(
        max_length=20,
        default="unknown"
    )

    action = models.CharField(
        max_length=100
    )

    description = models.TextField()

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ['-created_at']

    @property
    def action_display(self):
        return self.action.replace('_', ' ').title()

    def __str__(self):
        return f"{self.user.username} - {self.action}"
    
from django.conf import settings
from django.db import models


class AdminActionLog(models.Model):

    admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="admin_actions"
    )

    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="targeted_actions",
        null=True,
        blank=True
    )

    action = models.CharField(
        max_length=255
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.admin.username} -> {self.target_user.username}"
    

