from pqr.models import PQR, Ciudadano, Seguimiento


def test_crear_pqr_publico_no_requiere_autenticacion(api_client, db):
    payload = {
        "tipo": "peticion",
        "titulo": "Copia de historia clínica",
        "descripcion": "Solicito copia de mi historia clínica de los últimos 6 meses.",
        "categoria": "historias_clinicas",
        "prioridad": "media",
        "canal": "web",
        "solicitante": {
            "nombre": "María",
            "apellido": "Gómez",
            "identificacion": "1000111222",
            "email": "maria.gomez@example.com",
            "telefono": "3009998877",
        },
    }

    respuesta = api_client.post("/api/pqr", payload, format="json")

    assert respuesta.status_code == 201
    assert respuesta.data["radicado"].startswith("PQR-")
    assert respuesta.data["estado"] == "recibida"
    assert PQR.objects.count() == 1
    assert Ciudadano.objects.filter(identificacion="1000111222").exists()


def test_crear_pqr_reutiliza_ciudadano_por_identificacion(api_client, ciudadano):
    payload = {
        "tipo": "queja",
        "titulo": "Demora en la atención",
        "descripcion": "La cita se demoró más de dos horas.",
        "categoria": "atencion",
        "solicitante": {
            "nombre": ciudadano.nombre,
            "apellido": ciudadano.apellido,
            "identificacion": ciudadano.identificacion,
            "email": ciudadano.email,
            "telefono": ciudadano.telefono,
        },
    }

    api_client.post("/api/pqr", payload, format="json")

    assert Ciudadano.objects.count() == 1
    assert PQR.objects.get().solicitante_id == ciudadano.id


def test_listar_pqr_requiere_autenticacion(api_client):
    respuesta = api_client.get("/api/pqr")
    assert respuesta.status_code == 401


def test_listar_pqr_con_filtro_por_estado(auth_client, pqr):
    otra = PQR.objects.create(
        tipo=PQR.Tipo.RECLAMO,
        titulo="Cobro indebido",
        descripcion="Me cobraron dos veces el mismo servicio.",
        categoria="facturacion",
        solicitante=pqr.solicitante,
        estado=PQR.Estado.EN_GESTION,
    )

    respuesta = auth_client.get("/api/pqr", {"estado": "en_gestion"})

    assert respuesta.status_code == 200
    radicados = [item["radicado"] for item in respuesta.data["results"]]
    assert otra.radicado in radicados
    assert pqr.radicado not in radicados


def test_detalle_pqr_requiere_autenticacion(api_client, pqr):
    respuesta = api_client.get(f"/api/pqr/{pqr.id}")
    assert respuesta.status_code == 401


def test_detalle_pqr_incluye_solicitante_y_seguimientos(auth_client, pqr):
    respuesta = auth_client.get(f"/api/pqr/{pqr.id}")

    assert respuesta.status_code == 200
    assert respuesta.data["solicitante"]["identificacion"] == pqr.solicitante.identificacion
    assert respuesta.data["seguimientos"] == []


def test_buscar_por_radicado_es_publico_y_no_expone_datos_del_solicitante(api_client, pqr):
    respuesta = api_client.get("/api/pqr/buscar", {"radicado": pqr.radicado})

    assert respuesta.status_code == 200
    assert respuesta.data["radicado"] == pqr.radicado
    assert "solicitante" not in respuesta.data


def test_buscar_por_radicado_inexistente_devuelve_404(api_client, db):
    respuesta = api_client.get("/api/pqr/buscar", {"radicado": "PQR-2026-999999"})
    assert respuesta.status_code == 404


def test_cambiar_estado_con_transicion_valida(auth_client, pqr):
    respuesta = auth_client.patch(
        f"/api/pqr/{pqr.id}/estado", {"estado": "en_gestion"}, format="json"
    )

    assert respuesta.status_code == 200
    assert respuesta.data["estado"] == "en_gestion"
    assert Seguimiento.objects.filter(pqr=pqr, tipo_accion="cambio_estado").exists()


def test_cambiar_estado_con_transicion_invalida_es_rechazada(auth_client, pqr):
    respuesta = auth_client.patch(
        f"/api/pqr/{pqr.id}/estado", {"estado": "resuelta"}, format="json"
    )

    assert respuesta.status_code == 400
    pqr.refresh_from_db()
    assert pqr.estado == PQR.Estado.RECIBIDA


def test_agregar_seguimiento_queda_en_el_historial(auth_client, pqr):
    respuesta = auth_client.post(
        f"/api/pqr/{pqr.id}/seguimiento",
        {"descripcion": "Se contactó al solicitante por teléfono.", "tipo_accion": "comentario"},
        format="json",
    )

    assert respuesta.status_code == 201

    historial = auth_client.get(f"/api/pqr/{pqr.id}/seguimiento")
    assert historial.status_code == 200
    assert len(historial.data) == 1
    assert historial.data[0]["usuario_nombre"] == "Ana Agente"


def test_estadisticas_requiere_autenticacion(api_client):
    respuesta = api_client.get("/api/estadisticas")
    assert respuesta.status_code == 401


def test_estadisticas_cuenta_pqr_por_estado(auth_client, pqr):
    respuesta = auth_client.get("/api/estadisticas")

    assert respuesta.status_code == 200
    assert respuesta.data["total"] == 1
    assert {"estado": "recibida", "total": 1} in respuesta.data["por_estado"]
