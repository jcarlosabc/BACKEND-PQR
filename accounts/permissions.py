from rest_framework.permissions import BasePermission


class EsSupervisorOAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and request.user.puede_supervisar
        )


class EsAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.rol == request.user.Rol.ADMIN
        )


class PuedeGestionarPQR(BasePermission):
    """Un agente solo gestiona PQR sin asignar o asignadas a él mismo.
    Supervisor y admin gestionan cualquier PQR."""

    def has_object_permission(self, request, view, obj):
        if request.user.puede_supervisar:
            return True
        return obj.agente_asignado_id in (None, request.user.id)
