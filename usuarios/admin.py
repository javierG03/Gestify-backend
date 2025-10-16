# admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, TipoDocumento

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = (
        'username', 'email', 'first_name', 'last_name', 'phone', 'birth_date',
        'document_type', 'document', 'country', 'city', 'is_staff', 'is_active', 'get_groups'
    )
    list_filter = ('is_staff', 'is_active', 'groups', 'country', 'city', 'document_type')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'document')
    ordering = ('username',)

    fieldsets = (
        (None, {"fields": (
            "username", "email", "first_name", "last_name", "phone", "birth_date",
            "document_type", "document", "country", "city", "password"
        )}),
        ("Auditoría", {"fields": ("created_at", "updated_at")}),
        ("Permissions", {"fields": ("is_staff", "is_active", "groups", "user_permissions")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "username", "email", "first_name", "last_name", "phone", "birth_date",
                "document_type", "document", "country", "city", "password1", "password2",
                "is_staff", "is_active", "groups", "user_permissions"
            ),
        }),
    )

    readonly_fields = ('created_at', 'updated_at')

    def get_groups(self, obj):
        return ", ".join(group.name for group in obj.groups.all())
    get_groups.short_description = "Roles"

@admin.register(TipoDocumento)
class TipoDocumentoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'codigo')
    search_fields = ('nombre',)