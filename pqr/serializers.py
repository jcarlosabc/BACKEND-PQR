from django.db import transaction
from rest_framework import serializers

from .models import PQR, Ciudadano, Seguimiento


class CiudadanoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ciudadano
        fields = ["id", "nombre", "apellido", "identificacion", "email", "telefono"]


class SeguimientoSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.CharField(source="usuario.nombre", default=None, read_only=True)

    class Meta:
        model = Seguimiento
        fields = ["id", "descripcion", "tipo_accion", "usuario_nombre", "fecha_registro"]
        read_only_fields = ["fecha_registro"]


class PQRListSerializer(serializers.ModelSerializer):
    solicitante_nombre = serializers.CharField(source="solicitante.nombre_completo", read_only=True)
    agente_asignado_nombre = serializers.CharField(
        source="agente_asignado.nombre", default=None, read_only=True
    )
    sla_estado = serializers.CharField(read_only=True)

    class Meta:
        model = PQR
        fields = [
            "id",
            "radicado",
            "tipo",
            "titulo",
            "categoria",
            "prioridad",
            "estado",
            "canal",
            "solicitante_nombre",
            "agente_asignado_nombre",
            "fecha_limite",
            "sla_estado",
            "created_at",
            "updated_at",
        ]


class PQRDetailSerializer(serializers.ModelSerializer):
    solicitante = CiudadanoSerializer(read_only=True)
    agente_asignado_nombre = serializers.CharField(
        source="agente_asignado.nombre", default=None, read_only=True
    )
    seguimientos = SeguimientoSerializer(many=True, read_only=True)
    sla_estado = serializers.CharField(read_only=True)
    puede_calificarse = serializers.BooleanField(read_only=True)

    class Meta:
        model = PQR
        fields = [
            "id",
            "radicado",
            "tipo",
            "titulo",
            "descripcion",
            "categoria",
            "prioridad",
            "estado",
            "canal",
            "solicitante",
            "agente_asignado_id",
            "agente_asignado_nombre",
            "seguimientos",
            "fecha_limite",
            "sla_estado",
            "calificacion",
            "comentario_calificacion",
            "puede_calificarse",
            "created_at",
            "updated_at",
        ]


class SolicitanteInputSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ciudadano
        fields = ["nombre", "apellido", "identificacion", "email", "telefono"]
        extra_kwargs = {"identificacion": {"validators": []}}


class PQRCreateSerializer(serializers.ModelSerializer):
    solicitante = SolicitanteInputSerializer()

    class Meta:
        model = PQR
        fields = ["tipo", "titulo", "descripcion", "categoria", "prioridad", "canal", "solicitante"]

    def create(self, validated_data):
        solicitante_data = validated_data.pop("solicitante")
        with transaction.atomic():
            ciudadano, _ = Ciudadano.objects.get_or_create(
                identificacion=solicitante_data["identificacion"],
                defaults=solicitante_data,
            )
            pqr = PQR.objects.create(solicitante=ciudadano, **validated_data)
        return pqr

    def to_representation(self, instance):
        return PQRDetailSerializer(instance, context=self.context).data


class PQRBuscarSerializer(serializers.ModelSerializer):
    sla_estado = serializers.CharField(read_only=True)
    puede_calificarse = serializers.BooleanField(read_only=True)

    class Meta:
        model = PQR
        fields = [
            "radicado",
            "tipo",
            "categoria",
            "prioridad",
            "estado",
            "fecha_limite",
            "sla_estado",
            "puede_calificarse",
            "created_at",
            "updated_at",
        ]


class CambiarEstadoSerializer(serializers.Serializer):
    estado = serializers.ChoiceField(choices=PQR.Estado.choices, required=False)
    prioridad = serializers.ChoiceField(choices=PQR.Prioridad.choices, required=False)

    def validate(self, attrs):
        if "estado" not in attrs and "prioridad" not in attrs:
            raise serializers.ValidationError("Debes enviar al menos 'estado' o 'prioridad'.")
        pqr = self.context["pqr"]
        nuevo_estado = attrs.get("estado")
        if nuevo_estado and nuevo_estado != pqr.estado and not pqr.transicion_valida(nuevo_estado):
            raise serializers.ValidationError(
                f"No se puede pasar de '{pqr.get_estado_display()}' a "
                f"'{PQR.Estado(nuevo_estado).label}'."
            )
        return attrs


class AgregarSeguimientoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Seguimiento
        fields = ["descripcion", "tipo_accion"]


class AsignarAgenteSerializer(serializers.Serializer):
    agente_id = serializers.IntegerField()

    def validate_agente_id(self, value):
        from accounts.models import Usuario

        if not Usuario.objects.filter(id=value, is_active=True).exists():
            raise serializers.ValidationError("El usuario indicado no existe o no está activo.")
        return value


class CalificarPQRSerializer(serializers.Serializer):
    radicado = serializers.CharField()
    calificacion = serializers.IntegerField(min_value=1, max_value=5)
    comentario = serializers.CharField(required=False, allow_blank=True)

    def validate_radicado(self, value):
        try:
            pqr = PQR.objects.get(radicado__iexact=value)
        except PQR.DoesNotExist as exc:
            raise serializers.ValidationError("No existe ninguna PQR con ese radicado.") from exc
        if not pqr.puede_calificarse:
            raise serializers.ValidationError(
                "Esta PQR no admite calificación (debe estar cerrada y no calificada antes)."
            )
        self.pqr = pqr
        return value
