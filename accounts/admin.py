from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Stock Ledger role", {"fields": ("role", "warehouse")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Stock Ledger role", {"fields": ("role", "warehouse")}),
    )
    list_display = ("username", "role", "warehouse", "is_staff")
    list_filter = ("role", "is_staff")
