def test_login_con_credenciales_validas_devuelve_tokens(api_client, agente):
    respuesta = api_client.post(
        "/api/auth/login",
        {"email": "agente@sersocial.test", "password": "Agente123!"},
        format="json",
    )

    assert respuesta.status_code == 200
    assert "access" in respuesta.data
    assert "refresh" in respuesta.data


def test_login_con_credenciales_invalidas_es_rechazado(api_client, agente):
    respuesta = api_client.post(
        "/api/auth/login",
        {"email": "agente@sersocial.test", "password": "incorrecta"},
        format="json",
    )

    assert respuesta.status_code == 401


def test_me_requiere_autenticacion(api_client):
    respuesta = api_client.get("/api/auth/me")
    assert respuesta.status_code == 401


def test_me_devuelve_datos_del_usuario_autenticado(auth_client, agente):
    respuesta = auth_client.get("/api/auth/me")

    assert respuesta.status_code == 200
    assert respuesta.data["email"] == agente.email
    assert respuesta.data["rol"] == "agente"
