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
    text_message = (
        f"Hola {user.first_name},\n\n"
        "Por favor verifica tu correo haciendo clic en el siguiente enlace:\n"
        f"{verification_url}\n\nSi no creaste esta cuenta, ignora este mensaje."
    )
    html_message = f"""
    <!DOCTYPE html>
    <html lang='es'>
    <head><meta charset='UTF-8'></head>
    <body style='margin:0;padding:0;background:#f5f6fa;font-family:Arial,Helvetica,sans-serif;'>
        <table width='100%' bgcolor='#f5f6fa' cellpadding='0' cellspacing='0'>
            <tr><td align='center'>
                <table width='480' style='background:#fff;border-radius:12px;box-shadow:0 2px 8px #0001;margin:40px 0;'>
                    <tr><td style='padding:32px 32px 16px 32px;text-align:center;'>
                        <div style="font-size:32px;font-weight:bold;background:linear-gradient(90deg,#2563eb,#a21caf);-webkit-background-clip:text;-webkit-text-fill-color:transparent;color:#ffffff;">Gestify</div>
                        <h2 style='color:#222222;margin:24px 0 8px 0;'>Verifica tu correo electrónico</h2>
                        <p style='color:#444444;margin:0 0 24px 0;'>Hola, <b>{user.first_name}</b>:</p>
                        <p style='color:#444444;margin:0 0 24px 0;'>Por favor, haz clic en el siguiente botón para verificar tu cuenta y activar tu acceso a <b style="color:#a21caf;">Gestify</b>.</p>
                        <a href='{verification_url}' style='display:inline-block;padding:14px 32px;background:linear-gradient(90deg,#2563eb,#a21caf);color:#fff;text-decoration:none;font-weight:bold;border-radius:8px;font-size:16px;margin-bottom:16px;'>Verificar mi correo</a>
                        <p style='color:#888888;font-size:13px;margin:24px 0 0 0;'>Si el botón no funciona, copia y pega este enlace en tu navegador:</p>
                        <p style='word-break:break-all;color:#2563eb;font-size:13px;margin:8px 0 0 0;'>{verification_url}</p>
                        <p style='color:#aaaaaa;font-size:12px;margin:32px 0 0 0;'>Si no creaste esta cuenta, ignora este mensaje.</p>
                        <hr style='border:none;border-top:1px solid #eee;margin:32px 0 16px 0;'>
                        <p style='color:#888;font-size:13px;margin:0;'>¡Gracias por unirte a Gestify! Si tienes dudas, contáctanos en <a href='mailto:soporte@gestify.com' style='color:#2563eb;text-decoration:none;'>soporte@gestify.com</a>.</p>
                    </td></tr>
                </table>
            </td></tr>
        </table>
    </body>
    </html>
    """
    from django.core.mail import EmailMultiAlternatives
    email = EmailMultiAlternatives(subject, text_message, settings.DEFAULT_FROM_EMAIL, [user.email])
    email.attach_alternative(html_message, "text/html")
    email.send()


def send_confirmation_email(user):
    subject = "Registro exitoso"
    text_message = (
        f"Hola {user.first_name},\n\n"
        "Tu cuenta ha sido verificada y el registro fue exitoso. ¡Bienvenido a Gestify!"
    )
    html_message = f"""
    <!DOCTYPE html>
    <html lang='es'>
    <head><meta charset='UTF-8'></head>
    <body style='margin:0;padding:0;background:#f5f6fa;font-family:Arial,Helvetica,sans-serif;'>
        <table width='100%' bgcolor='#f5f6fa' cellpadding='0' cellspacing='0'>
            <tr><td align='center'>
                <table width='480' style='background:#fff;border-radius:12px;box-shadow:0 2px 8px #0001;margin:40px 0;'>
                    <tr><td style='padding:32px 32px 16px 32px;text-align:center;'>
                        <div style="font-size:32px;font-weight:bold;background:linear-gradient(90deg,#2563eb,#a21caf);-webkit-background-clip:text;-webkit-text-fill-color:transparent;color:#ffffff;">Gestify</div>
                        <h2 style='color:#222222;margin:24px 0 8px 0;'>¡Registro exitoso!</h2>
                        <p style='color:#444444;margin:0 0 24px 0;'>Hola, <b>{user.first_name}</b>:</p>
                        <p style='color:#444444;margin:0 0 24px 0;'>Tu cuenta ha sido verificada y el registro fue exitoso.<br>¡Bienvenido a <b style="color:#a21caf;">Gestify</b>!</p>
                        <p style='color:#888888;font-size:13px;margin:32px 0 0 0;'>Ahora puedes acceder a todas las funcionalidades de la plataforma.</p>
                        <hr style='border:none;border-top:1px solid #eee;margin:32px 0 16px 0;'>
                        <p style='color:#888;font-size:13px;margin:0;'>¡Gracias por unirte a Gestify! Si tienes dudas, contáctanos en <a href='mailto:soporte@gestify.com' style='color:#2563eb;text-decoration:none;'>soporte@gestify.com</a>.</p>
                    </td></tr>
                </table>
            </td></tr>
        </table>
    </body>
    </html>
    """
    from django.core.mail import EmailMultiAlternatives
    email = EmailMultiAlternatives(subject, text_message, settings.DEFAULT_FROM_EMAIL, [user.email])
    email.attach_alternative(html_message, "text/html")
    email.send()


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
