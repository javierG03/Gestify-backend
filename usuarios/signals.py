"""Señales para auditoría y gestión de grupos en el módulo de usuarios."""

import logging

from django.contrib.auth.models import Group, Permission
from django.db import transaction
from django.db.models.signals import post_migrate, pre_save
from django.dispatch import receiver

from .models import CustomUser, UserChangeLog

logger = logging.getLogger(__name__)

@receiver(pre_save, sender=CustomUser)
def log_user_changes(sender, instance, **kwargs):
    """Registra cambios relevantes en el usuario para auditoría."""
    if not instance.pk:
        return  # Solo para actualizaciones, no creación
    try:
        old_user = CustomUser.objects.get(pk=instance.pk)
    except CustomUser.DoesNotExist:
        return
    fields_to_track = ["email", "first_name", "last_name", "phone", "birth_date", "department_id", "city_id"]
    for field in fields_to_track:
        old_value = getattr(old_user, field, None)
        new_value = getattr(instance, field, None)
        if old_value != new_value:
            UserChangeLog.objects.create(
                user=instance,
                changed_by=getattr(instance, '_changed_by', None),
                change_type="datos personales" if field != "email" else "email",
                field_changed=field,
                old_value=str(old_value),
                new_value=str(new_value)
            )

GROUP_PERMISSION_MAP = {
    "Organizador": [
        "add_event",
        "change_event",
        "delete_event",
        "view_event",
        "add_ticket",
        "change_ticket",
        "view_ticket",
    ],
    "Participante": [
        "view_event",
        "inscribirse_evento",
    ],
    "Staff": [
        "view_ticket",
        "change_ticket",
        "view_ticketaccesslog",
    ],
}


@receiver(post_migrate)
def create_user_groups(sender, **kwargs):
    """Crea grupos por defecto y sincroniza sus permisos tras las migraciones."""
    app_config = kwargs.get("app_config")
    if not app_config or app_config.label not in {"usuarios", "eventos"}:
        return

    with transaction.atomic():
        for group_name, perm_codenames in GROUP_PERMISSION_MAP.items():
            group, _ = Group.objects.get_or_create(name=group_name)
            permissions_qs = Permission.objects.filter(codename__in=perm_codenames)
            assigned = set(permissions_qs.values_list("codename", flat=True))
            missing = set(perm_codenames) - assigned
            if missing and app_config.label == "eventos":
                logger.warning("Permisos no encontrados para el grupo %s: %s", group_name, ", ".join(sorted(missing)))
            if permissions_qs.exists():
                group.permissions.set(permissions_qs)

        admin_group, _ = Group.objects.get_or_create(name="Administrador")
        admin_group.permissions.set(Permission.objects.all())