"""Servicios de email y administración de tokens para el módulo de usuarios."""

import secrets
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.core.exceptions import ImproperlyConfigured
from django.utils import timezone

from .models import UserToken


def _create_token(user, token_type, hours_valid):
    """Crea un token persistente e invalida tokens previos del mismo tipo."""
    now = timezone.now()
    UserToken.objects.filter(
        user=user,
        token_type=token_type,
        is_used=False,
        expires_at__gt=now,
    ).update(is_used=True)
    token_value = secrets.token_urlsafe(32)
    UserToken.objects.create(
        user=user,
        token=token_value,
        token_type=token_type,
        expires_at=now + timedelta(hours=hours_valid),
    )
    return token_value


def create_email_verification_token(user):
    return _create_token(user, UserToken.TokenType.EMAIL_VERIFICATION, hours_valid=24)


def _send_email(subject, message, recipient):
    if not getattr(settings, "DEFAULT_FROM_EMAIL", None):
        raise ImproperlyConfigured("DEFAULT_FROM_EMAIL no está configurado.")
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [recipient],
        fail_silently=False,
    )


def send_verification_email(user, token):
    if not getattr(settings, "FRONTEND_URL", None):
        raise ImproperlyConfigured("FRONTEND_URL no está configurado.")
    verification_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"
    subject = "Verifica tu correo electrónico"
    message = (
        f"Hola {user.first_name},\n\n"
        "Por favor verifica tu correo haciendo clic en el siguiente enlace:\n"
        f"{verification_url}\n\nSi no creaste esta cuenta, ignora este mensaje."
    )
    _send_email(subject, message, user.email)


def send_confirmation_email(user):
    subject = "Registro exitoso"
    message = (
        f"Hola {user.first_name},\n\n"
        "Tu cuenta ha sido verificada y el registro fue exitoso. ¡Bienvenido a Gestify!"
    )
    _send_email(subject, message, user.email)


def create_password_reset_token(user):
    return _create_token(user, UserToken.TokenType.PASSWORD_RESET, hours_valid=1)


def send_password_reset_email(user, token):
    if not getattr(settings, "FRONTEND_URL", None):
        raise ImproperlyConfigured("FRONTEND_URL no está configurado.")
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    subject = "Recuperación de contraseña"
    message = (
        f"Hola {user.first_name},\n\n"
        "Para restablecer tu contraseña, haz clic en el siguiente enlace:\n"
        f"{reset_url}\n\nSi no solicitaste este cambio, ignora este mensaje."
    )
    _send_email(subject, message, user.email)
