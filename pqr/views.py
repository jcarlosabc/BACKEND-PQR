from django.db.models import Count
from django.shortcuts import get_object_or_404
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .filters import PQRFilter
from .models import PQR, Seguimiento
from .notifications import notificar_cambio_estado, notificar_creacion
from .serializers import (
    AgregarSeguimientoSerializer,
    CambiarEstadoSerializer,
    PQRBuscarSerializer,
    PQRCreateSerializer,
    PQRDetailSerializer,
    PQRListSerializer,
    SeguimientoSerializer,
)


class PQRViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = PQR.objects.select_related("solicitante", "agente_asignado").prefetch_related(
        "seguimientos__usuario"
    )
    filterset_class = PQRFilter

    def get_permissions(self):
        if self.action in ("create", "buscar"):
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == "list":
            return PQRListSerializer
        if self.action == "create":
            return PQRCreateSerializer
        if self.action == "buscar":
            return PQRBuscarSerializer
        return PQRDetailSerializer

    def perform_create(self, serializer):
        pqr = serializer.save()
        notificar_creacion(pqr)

    @action(detail=True, methods=["patch"], url_path="estado")
    def cambiar_estado(self, request, pk=None):
        pqr = self.get_object()
        serializer = CambiarEstadoSerializer(data=request.data, context={"pqr": pqr})
        serializer.is_valid(raise_exception=True)
        datos = serializer.validated_data

        cambios = []
        estado_cambio = False
        if "estado" in datos and datos["estado"] != pqr.estado:
            anterior = pqr.get_estado_display()
            pqr.estado = datos["estado"]
            cambios.append(f"Estado: {anterior} -> {pqr.get_estado_display()}")
            estado_cambio = True
        if "prioridad" in datos and datos["prioridad"] != pqr.prioridad:
            anterior = pqr.get_prioridad_display()
            pqr.prioridad = datos["prioridad"]
            cambios.append(f"Prioridad: {anterior} -> {pqr.get_prioridad_display()}")

        if cambios:
            pqr.save(update_fields=["estado", "prioridad", "updated_at"])
            Seguimiento.objects.create(
                pqr=pqr,
                descripcion=" · ".join(cambios),
                tipo_accion=Seguimiento.TipoAccion.CAMBIO_ESTADO,
                usuario=request.user,
            )
            if estado_cambio:
                notificar_cambio_estado(pqr)

        return Response(PQRDetailSerializer(pqr).data)

    @action(detail=True, methods=["get", "post"], url_path="seguimiento")
    def seguimiento(self, request, pk=None):
        pqr = self.get_object()

        if request.method == "GET":
            serializer = SeguimientoSerializer(pqr.seguimientos.all(), many=True)
            return Response(serializer.data)

        serializer = AgregarSeguimientoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        entrada = serializer.save(pqr=pqr, usuario=request.user)
        return Response(SeguimientoSerializer(entrada).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"], url_path="buscar")
    def buscar(self, request):
        radicado = request.query_params.get("radicado", "").strip()
        if not radicado:
            return Response(
                {"detail": "Debes indicar el parámetro 'radicado'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        pqr = get_object_or_404(PQR, radicado__iexact=radicado)
        return Response(PQRBuscarSerializer(pqr).data)


class EstadisticasView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            "total": PQR.objects.count(),
            "por_estado": list(
                PQR.objects.values("estado").order_by("estado").annotate(total=Count("id"))
            ),
            "por_tipo": list(
                PQR.objects.values("tipo").order_by("tipo").annotate(total=Count("id"))
            ),
            "por_prioridad": list(
                PQR.objects.values("prioridad").order_by("prioridad").annotate(total=Count("id"))
            ),
        })
