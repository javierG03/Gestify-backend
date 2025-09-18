# usuarios/signals.py
from django.apps import apps
from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.contrib.auth.models import Group, Permission
from django.conf import settings

@receiver(post_migrate)
def create_user_groups(sender, **kwargs):
    """
    Crea grupos y les asigna permisos. Se ejecuta después de migrate.
    """
    # Mapas grupo -> lista de codenames de permisos
    groups_permissions = {
        "Administrador": [
            "añadir_evento", "cambiar_evento", "eliminar_evento",
            "ver_evento", "cancelar_evento", "administrar_pagos"
        ],
        "Organizador": [
            "cambiar_evento", "ver_evento", "administrar_pagos"
        ],
        "Participante": [
            "ver_evento", "unirse_evento"
        ],
    }

    for group_name, perm_codenames in groups_permissions.items():
        group, created = Group.objects.get_or_create(name=group_name)
        for codename in perm_codenames:
            try:
                perm = Permission.objects.get(codename=codename)
                group.permissions.add(perm)
            except Permission.DoesNotExist:
                # si la permission no existe aún (por ejemplo no migró el app), la ignoramos por ahora
                # Podrías registrar/loggear aquí para comprobarlo
                pass
