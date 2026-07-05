from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import Usuario
from .permissions import EsAdmin, EsSupervisorOAdmin
from .serializers import (
    UsuarioActualizarSerializer,
    UsuarioCreateSerializer,
    UsuarioSerializer,
    UsuarioTokenObtainPairSerializer,
)


class LoginView(TokenObtainPairView):
    serializer_class = UsuarioTokenObtainPairSerializer


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UsuarioSerializer(request.user).data)


class UsuarioViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """Listar (para el combo de reasignación) es de supervisor/admin.
    Crear y editar (rol, activo/inactivo) es exclusivo de admin."""

    queryset = Usuario.objects.all().order_by("nombre")
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_permissions(self):
        if self.action == "list":
            return [IsAuthenticated(), EsSupervisorOAdmin()]
        return [IsAuthenticated(), EsAdmin()]

    def get_serializer_class(self):
        if self.action == "create":
            return UsuarioCreateSerializer
        if self.action == "partial_update":
            return UsuarioActualizarSerializer
        return UsuarioSerializer
