"""
usuarios/models.py
Modelos principales del módulo de usuarios: CustomUser, DocumentType, UserChangeLog.
"""

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

class DocumentType(models.Model):
    """Tipo de documento normalizado (cédula, pasaporte, etc)."""
    name = models.CharField(max_length=50, unique=True, help_text="Nombre del tipo de documento")
    code = models.CharField(max_length=10, unique=True, help_text="Código del tipo de documento")

    class Meta:
        verbose_name = "Document type"
        verbose_name_plural = "Document types"
        ordering = ["name"]
        db_table = "users_document_type"

    def __str__(self):
        return f"{self.name} ({self.code})"

class CustomUser(AbstractUser):
    """Usuario personalizado basado en AbstractUser."""
    username = models.CharField(max_length=150, unique=True)
    first_name = models.CharField(max_length=150, help_text="Nombres")
    last_name = models.CharField(max_length=150, help_text="Apellidos")
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True, null=True, help_text="Teléfono de contacto")
    birth_date = models.DateField(blank=True, null=True, help_text="Fecha de nacimiento")
    document_type = models.ForeignKey(DocumentType, on_delete=models.SET_NULL, blank=True, null=True, help_text="Tipo de documento")
    document = models.CharField(max_length=30, blank=True, null=True, unique=True, help_text="Número de documento")
    country = models.CharField(max_length=50, blank=True, null=True, default="Colombia", help_text="País de residencia")
    created_at = models.DateTimeField(auto_now_add=True, help_text="Fecha de creación del usuario")
    updated_at = models.DateTimeField(auto_now=True, help_text="Fecha de última actualización del usuario")
    department = models.ForeignKey('eventos.Department', on_delete=models.SET_NULL, blank=True, null=True, help_text="Departamento de residencia (solo Colombia)")
    city = models.ForeignKey('eventos.City', on_delete=models.SET_NULL, blank=True, null=True, help_text="Ciudad de residencia (solo Colombia)")
    city_text = models.CharField(max_length=100, blank=True, null=True, help_text="Ciudad libre (otros países)")
    department_text = models.CharField(max_length=100, blank=True, null=True, help_text="Departamento/Región libre (otros países)")
    is_email_verified = models.BooleanField(default=False, help_text="Indica si el email ha sido verificado")

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "first_name", "last_name"]

    class Meta:
        db_table = "users_custom_user"

    def __str__(self):
        return f"{self.email}"

class UserChangeLog(models.Model):
    """Historial de cambios realizados sobre el usuario (auditoría)."""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='change_logs')
    changed_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='performed_changes', help_text="Usuario que realizó el cambio")
    change_type = models.CharField(max_length=50, help_text="Tipo de cambio: email, password, datos personales")
    field_changed = models.CharField(max_length=50, help_text="Campo modificado")
    old_value = models.TextField(blank=True, null=True, help_text="Valor anterior")
    new_value = models.TextField(blank=True, null=True, help_text="Nuevo valor")
    timestamp = models.DateTimeField(auto_now_add=True, help_text="Fecha y hora del cambio")

    class Meta:
        verbose_name = "User Change Log"
        verbose_name_plural = "User Change Logs"
        ordering = ["-timestamp"]
        db_table = "users_change_log"

    def __str__(self):
        return f"{self.user.email} - {self.change_type} - {self.field_changed} ({self.timestamp})"


class UserToken(models.Model):
    """Tokens persistentes para verificación de correo y recuperación de contraseña."""

    class TokenType(models.TextChoices):
        EMAIL_VERIFICATION = "email_verification", "Email Verification"
        PASSWORD_RESET = "password_reset", "Password Reset"

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="tokens")
    token = models.CharField(max_length=64, unique=True)
    token_type = models.CharField(max_length=32, choices=TokenType.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        db_table = "users_token"
        indexes = [
            models.Index(fields=["token", "token_type"]),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.token_type}"

    def mark_used(self) -> None:
        if not self.is_used:
            self.is_used = True
            self.save(update_fields=["is_used"])

    def is_valid(self) -> bool:
        return (not self.is_used) and self.expires_at >= timezone.now()

