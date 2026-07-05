from rest_framework.test import APIClient

from pqr.models import Seguimiento


def test_agente_puede_gestionar_pqr_sin_asignar(auth_client, pqr, agente):
    respuesta = auth_client.patch(
        f"/api/pqr/{pqr.id}/estado", {"estado": "en_gestion"}, format="json"
    )

    assert respuesta.status_code == 200
    pqr.refresh_from_db()
    assert pqr.agente_asignado_id == agente.id


def test_agente_no_puede_gestionar_pqr_asignada_a_otro_agente(auth_client, pqr, otro_agente):
    pqr.agente_asignado = otro_agente
    pqr.save(update_fields=["agente_asignado"])

    respuesta = auth_client.patch(
        f"/api/pqr/{pqr.id}/estado", {"estado": "en_gestion"}, format="json"
    )

    assert respuesta.status_code == 404


def test_agente_no_ve_en_el_listado_pqr_asignadas_a_otro(auth_client, pqr, otro_agente):
    pqr.agente_asignado = otro_agente
    pqr.save(update_fields=["agente_asignado"])

    respuesta = auth_client.get("/api/pqr")

    radicados = [item["radicado"] for item in respuesta.data["results"]]
    assert pqr.radicado not in radicados


def test_supervisor_ve_y_gestiona_pqr_de_cualquier_agente(supervisor_client, pqr, otro_agente):
    pqr.agente_asignado = otro_agente
    pqr.save(update_fields=["agente_asignado"])

    listado = supervisor_client.get("/api/pqr")
    radicados = [item["radicado"] for item in listado.data["results"]]
    assert pqr.radicado in radicados

    respuesta = supervisor_client.patch(
        f"/api/pqr/{pqr.id}/estado", {"estado": "en_gestion"}, format="json"
    )
    assert respuesta.status_code == 200


def test_solo_supervisor_o_admin_pueden_reasignar(auth_client, pqr, otro_agente):
    respuesta = auth_client.patch(
        f"/api/pqr/{pqr.id}/asignar", {"agente_id": otro_agente.id}, format="json"
    )
    assert respuesta.status_code == 403


def test_supervisor_puede_reasignar_una_pqr(supervisor_client, pqr, agente, otro_agente):
    pqr.agente_asignado = agente
    pqr.save(update_fields=["agente_asignado"])

    respuesta = supervisor_client.patch(
        f"/api/pqr/{pqr.id}/asignar", {"agente_id": otro_agente.id}, format="json"
    )

    assert respuesta.status_code == 200
    pqr.refresh_from_db()
    assert pqr.agente_asignado_id == otro_agente.id
    assert Seguimiento.objects.filter(pqr=pqr, tipo_accion="asignacion").exists()


def test_reasignar_a_usuario_inexistente_falla(supervisor_client, pqr):
    respuesta = supervisor_client.patch(
        f"/api/pqr/{pqr.id}/asignar", {"agente_id": 9999}, format="json"
    )
    assert respuesta.status_code == 400


def test_listar_usuarios_requiere_supervisor_o_admin(agente, supervisor):
    cliente_agente = APIClient()
    cliente_agente.force_authenticate(user=agente)
    respuesta_agente = cliente_agente.get("/api/usuarios")
    assert respuesta_agente.status_code == 403

    cliente_supervisor = APIClient()
    cliente_supervisor.force_authenticate(user=supervisor)
    respuesta_supervisor = cliente_supervisor.get("/api/usuarios")
    assert respuesta_supervisor.status_code == 200


def test_supervisor_no_puede_crear_usuarios(supervisor_client):
    respuesta = supervisor_client.post(
        "/api/usuarios",
        {
            "nombre": "Nuevo Agente",
            "email": "nuevo@sersocial.test",
            "rol": "agente",
            "password": "ClaveSegura123!",
        },
        format="json",
    )
    assert respuesta.status_code == 403


def test_admin_puede_crear_usuarios(admin_client):
    from accounts.models import Usuario

    respuesta = admin_client.post(
        "/api/usuarios",
        {
            "nombre": "Nuevo Agente",
            "email": "nuevo@sersocial.test",
            "rol": "agente",
            "password": "ClaveSegura123!",
        },
        format="json",
    )

    assert respuesta.status_code == 201
    assert "password" not in respuesta.data
    creado = Usuario.objects.get(email="nuevo@sersocial.test")
    assert creado.check_password("ClaveSegura123!")
    assert creado.rol == "agente"
    assert creado.is_active is True


def test_admin_puede_desactivar_un_usuario(admin_client, agente):
    respuesta = admin_client.patch(
        f"/api/usuarios/{agente.id}", {"is_active": False}, format="json"
    )

    assert respuesta.status_code == 200
    agente.refresh_from_db()
    assert agente.is_active is False


def test_agente_desactivado_no_puede_iniciar_sesion(admin_client, agente, api_client):
    admin_client.patch(f"/api/usuarios/{agente.id}", {"is_active": False}, format="json")

    respuesta = api_client.post(
        "/api/auth/login",
        {"email": agente.email, "password": "Agente123!"},
        format="json",
    )
    assert respuesta.status_code == 401


def test_admin_puede_cambiar_el_rol_de_un_usuario(admin_client, agente):
    respuesta = admin_client.patch(
        f"/api/usuarios/{agente.id}", {"rol": "supervisor"}, format="json"
    )

    assert respuesta.status_code == 200
    agente.refresh_from_db()
    assert agente.rol == "supervisor"
