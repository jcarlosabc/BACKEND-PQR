from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Usuario


class UsuarioTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["nombre"] = user.nombre
        token["rol"] = user.rol
        return token


class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ["id", "nombre", "email", "rol", "is_active"]


class UsuarioCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = Usuario
        fields = ["id", "nombre", "email", "rol", "password"]
        read_only_fields = ["id"]

    def create(self, validated_data):
        password = validated_data.pop("password")
        return Usuario.objects.create_user(password=password, **validated_data)

    def to_representation(self, instance):
        return UsuarioSerializer(instance).data


class UsuarioActualizarSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ["rol", "is_active"]
        extra_kwargs = {
            "rol": {"required": False},
            "is_active": {"required": False},
        }

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("Debes enviar 'rol' y/o 'is_active'.")
        return attrs

    def to_representation(self, instance):
        return UsuarioSerializer(instance).data
