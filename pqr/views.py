import csv
import datetime

from django.db.models import Avg, Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Usuario
from accounts.permissions import EsSupervisorOAdmin, PuedeGestionarPQR

from .filters import PQRFilter
from .models import PQR, Seguimiento
from .notifications import notificar_cambio_estado, notificar_creacion
from .serializers import (
    AgregarSeguimientoSerializer,
    AsignarAgenteSerializer,
    CalificarPQRSerializer,
    CambiarEstadoSerializer,
    PQRBuscarSerializer,
    PQRCreateSerializer,
    PQRDetailSerializer,
    PQRListSerializer,
    SeguimientoSerializer,
)


def _asignar_automaticamente_si_corresponde(pqr, usuario):
    """Un agente que actúa sobre una PQR sin asignar la toma para sí.
    Supervisores y admins no disparan esta asignación implícita."""
    if usuario.puede_supervisar or pqr.agente_asignado_id is not None:
        return
    pqr.agente_asignado = usuario
    pqr.save(update_fields=["agente_asignado", "updated_at"])
    Seguimiento.objects.create(
        pqr=pqr,
        descripcion=f"Asignada automáticamente a {usuario.nombre} al iniciar gestión.",
        tipo_accion=Seguimiento.TipoAccion.ASIGNACION,
        usuario=usuario,
    )


class PQRViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    filterset_class = PQRFilter

    def get_queryset(self):
        queryset = PQR.objects.select_related("solicitante", "agente_asignado").prefetch_related(
            "seguimientos__usuario"
        )
        usuario = self.request.user
        if usuario.is_authenticated and not usuario.puede_supervisar:
            queryset = queryset.filter(Q(agente_asignado__isnull=True) | Q(agente_asignado=usuario))
        return queryset

    def get_permissions(self):
        if self.action in ("create", "buscar", "calificar"):
            return [AllowAny()]
        if self.action == "asignar":
            return [IsAuthenticated(), EsSupervisorOAdmin()]
        if self.action in ("cambiar_estado", "seguimiento"):
            return [IsAuthenticated(), PuedeGestionarPQR()]
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

        _asignar_automaticamente_si_corresponde(pqr, request.user)

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

        _asignar_automaticamente_si_corresponde(pqr, request.user)

        entrada = serializer.save(pqr=pqr, usuario=request.user)
        return Response(SeguimientoSerializer(entrada).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["patch"], url_path="asignar")
    def asignar(self, request, pk=None):
        pqr = self.get_object()
        serializer = AsignarAgenteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        nuevo_agente = Usuario.objects.get(id=serializer.validated_data["agente_id"])
        anterior = pqr.agente_asignado.nombre if pqr.agente_asignado_id else "sin asignar"

        pqr.agente_asignado = nuevo_agente
        pqr.save(update_fields=["agente_asignado", "updated_at"])
        Seguimiento.objects.create(
            pqr=pqr,
            descripcion=f"Reasignada de {anterior} a {nuevo_agente.nombre}.",
            tipo_accion=Seguimiento.TipoAccion.ASIGNACION,
            usuario=request.user,
        )
        return Response(PQRDetailSerializer(pqr).data)

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

    @action(detail=False, methods=["post"], url_path="calificar")
    def calificar(self, request):
        serializer = CalificarPQRSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        pqr = serializer.pqr
        pqr.calificacion = serializer.validated_data["calificacion"]
        pqr.comentario_calificacion = serializer.validated_data.get("comentario", "")
        pqr.save(update_fields=["calificacion", "comentario_calificacion"])

        return Response(PQRBuscarSerializer(pqr).data)

    @action(detail=False, methods=["get"], url_path="exportar")
    def exportar(self, request):
        queryset = self.filter_queryset(self.get_queryset())

        respuesta = HttpResponse(content_type="text/csv")
        respuesta["Content-Disposition"] = 'attachment; filename="pqr.csv"'
        escritor = csv.writer(respuesta)
        escritor.writerow(
            [
                "radicado",
                "tipo",
                "titulo",
                "categoria",
                "prioridad",
                "estado",
                "canal",
                "solicitante",
                "agente_asignado",
                "fecha_limite",
                "sla_estado",
                "creado",
                "actualizado",
            ]
        )
        for pqr in queryset:
            escritor.writerow(
                [
                    pqr.radicado,
                    pqr.get_tipo_display(),
                    pqr.titulo,
                    pqr.categoria,
                    pqr.get_prioridad_display(),
                    pqr.get_estado_display(),
                    pqr.get_canal_display(),
                    pqr.solicitante.nombre_completo,
                    pqr.agente_asignado.nombre if pqr.agente_asignado_id else "",
                    pqr.fecha_limite,
                    pqr.sla_estado,
                    pqr.created_at,
                    pqr.updated_at,
                ]
            )
        return respuesta


class EstadisticasView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        abiertas = PQR.objects.exclude(estado__in=[PQR.Estado.RESUELTA, PQR.Estado.CERRADA])
        hoy = timezone.now().date()

        return Response(
            {
                "total": PQR.objects.count(),
                "por_estado": list(
                    PQR.objects.values("estado").order_by("estado").annotate(total=Count("id"))
                ),
                "por_tipo": list(
                    PQR.objects.values("tipo").order_by("tipo").annotate(total=Count("id"))
                ),
                "por_prioridad": list(
                    PQR.objects.values("prioridad")
                    .order_by("prioridad")
                    .annotate(total=Count("id"))
                ),
                "vencidas": abiertas.filter(fecha_limite__lt=hoy).count(),
                "por_vencer": abiertas.filter(
                    fecha_limite__gte=hoy,
                    fecha_limite__lte=hoy + datetime.timedelta(days=3),
                ).count(),
                "calificacion_promedio": PQR.objects.filter(calificacion__isnull=False).aggregate(
                    promedio=Avg("calificacion")
                )["promedio"],
            }
        )
