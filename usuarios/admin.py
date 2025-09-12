# admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser  # importa tu modelo

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ('username', 'email', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_active')
    search_fields = ('username', 'email')
    ordering = ('username',)

     # Personalizamos fieldsets para que no pida first_name ni last_name
    fieldsets = (
        (None, {"fields": ("username", "email", "name", "password")}),
        ("Permissions", {"fields": ("is_staff", "is_active", "groups", "user_permissions")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("username", "email", "name", "password1", "password2", "is_staff", "is_active", "groups", "user_permissions"),
        }),
    )

    search_fields = ("username", "email")
    ordering = ("username",)