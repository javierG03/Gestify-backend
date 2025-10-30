"""
usuarios/permissions.py
Permisos personalizados para el módulo de usuarios. Clean code y comentarios claros.
"""
from rest_framework.permissions import BasePermission

class IsInGroup(BasePermission):
    """
    Permite acceso solo si el usuario pertenece a un grupo específico.
    Uso: crear subclases con group_name o instanciar con view.group_name
    """
    group_name = None
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        name = getattr(view, 'required_group', self.group_name)
        if not name:
            return False
        return request.user.groups.filter(name=name).exists()

class IsAdminGroup(IsInGroup):
    group_name = "Administrador"

class IsParticipante(IsInGroup):
    group_name = "Participante"


class IsStaffGroup(IsInGroup):
    group_name = "Staff"


class IsStaffOrAdmin(BasePermission):
    """Permite acceso a miembros del staff o administradores."""

    def has_permission(self, request, view):  # type: ignore[override]
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.groups.filter(name__in={"Administrador", "Staff"}).exists()


class IsSelfOrAdmin(BasePermission):
    """Permite acceso al propio usuario o a miembros del grupo Administrador."""

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.groups.filter(name="Administrador").exists():
            return True
        return obj == request.user