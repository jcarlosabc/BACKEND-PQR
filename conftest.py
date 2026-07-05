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
def otro_agente(db):
    return Usuario.objects.create_user(
        email="otro.agente@sersocial.test",
        password="Agente123!",
        nombre="Beto Agente",
        rol=Usuario.Rol.AGENTE,
    )


@pytest.fixture
def supervisor(db):
    return Usuario.objects.create_user(
        email="supervisor@sersocial.test",
        password="Supervisor123!",
        nombre="Sara Supervisora",
        rol=Usuario.Rol.SUPERVISOR,
    )


@pytest.fixture
def supervisor_client(api_client, supervisor):
    api_client.force_authenticate(user=supervisor)
    return api_client


@pytest.fixture
def admin(db):
    return Usuario.objects.create_user(
        email="admin@sersocial.test",
        password="Admin123!",
        nombre="Alex Admin",
        rol=Usuario.Rol.ADMIN,
        is_staff=True,
        is_superuser=True,
    )


@pytest.fixture
def admin_client(api_client, admin):
    api_client.force_authenticate(user=admin)
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
