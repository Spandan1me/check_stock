from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        VENDOR = "VENDOR", "Vendor"

    role = models.CharField(max_length=10, choices=Role.choices, default=Role.VENDOR)

    # A vendor user is tied to exactly one warehouse they are allowed to manage.
    # Admin users leave this blank - they see everything.
    warehouse = models.ForeignKey(
        "inventory.Warehouse",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="vendor_users",
    )

    @property
    def is_admin_role(self):
        return self.role == self.Role.ADMIN

    @property
    def is_vendor_role(self):
        return self.role == self.Role.VENDOR

    def __str__(self):
        return f"{self.username} ({self.role})"
