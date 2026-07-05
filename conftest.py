import pytest
from rest_framework.test import APIClient

from accounts.models import Usuario
from pqr.models import PQR, Ciudadano


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def agente(db):
    return Usuario.objects.create_user(
        email="agente@sersocial.test",
        password="Agente123!",
        nombre="Ana Agente",
        rol=Usuario.Rol.AGENTE,
    )


@pytest.fixture
def auth_client(api_client, agente):
    api_client.force_authenticate(user=agente)
    return api_client


@pytest.fixture
def ciudadano(db):
    return Ciudadano.objects.create(
        nombre="Carlos",
        apellido="Pérez",
        identificacion="123456789",
        email="carlos@example.com",
        telefono="3001234567",
    )


@pytest.fixture
def pqr(db, ciudadano):
    return PQR.objects.create(
        tipo=PQR.Tipo.PETICION,
        titulo="Solicitud de certificado",
        descripcion="Necesito un certificado de afiliación.",
        categoria="certificados",
        solicitante=ciudadano,
    )
