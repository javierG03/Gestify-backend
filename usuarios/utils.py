"""Utilidades generales del módulo de usuarios."""

from django.contrib.auth.models import Group


def assign_user_to_group(user, group_name: str) -> None:
    """Añade al usuario al grupo indicado si existe y evita duplicados."""
    try:
        group = Group.objects.get(name=group_name)
    except Group.DoesNotExist:
        return
    if not user.groups.filter(id=group.id).exists():
        user.groups.add(group)
