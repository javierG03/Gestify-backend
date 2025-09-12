from rest_framework.permissions import BasePermission

class IsInGroup(BasePermission):
    """
    Uso: crear subclases con group_name o instanciar con view.group_name
    """

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