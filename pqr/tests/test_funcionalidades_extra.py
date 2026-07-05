import datetime

from django.conf import settings
from django.utils import timezone

from pqr.models import PQR


def test_pqr_creada_tiene_fecha_limite_segun_sla(pqr):
    esperado = pqr.created_at.date() + datetime.timedelta(days=settings.PQR_DIAS_SLA)
    assert pqr.fecha_limite == esperado


def test_sla_estado_a_tiempo_para_pqr_recien_creada(pqr):
    assert pqr.sla_estado == "a_tiempo"


def test_sla_estado_vencida_si_paso_la_fecha_limite(pqr):
    pqr.fecha_limite = timezone.now().date() - datetime.timedelta(days=1)
    pqr.save(update_fields=["fecha_limite"])
    assert pqr.sla_estado == "vencida"


def test_sla_estado_por_vencer_dentro_de_tres_dias(pqr):
    pqr.fecha_limite = timezone.now().date() + datetime.timedelta(days=2)
    pqr.save(update_fields=["fecha_limite"])
    assert pqr.sla_estado == "por_vencer"


def test_filtro_vencidas_solo_muestra_pqr_abiertas_vencidas(auth_client, pqr, ciudadano):
    pqr.fecha_limite = timezone.now().date() - datetime.timedelta(days=1)
    pqr.save(update_fields=["fecha_limite"])

    al_dia = PQR.objects.create(
        tipo=PQR.Tipo.QUEJA,
        titulo="PQR al día",
        descripcion="Sin problema de plazo.",
        categoria="atencion",
        solicitante=ciudadano,
    )

    respuesta = auth_client.get("/api/pqr", {"vencidas": "true"})
    radicados = [item["radicado"] for item in respuesta.data["results"]]

    assert pqr.radicado in radicados
    assert al_dia.radicado not in radicados


def test_busqueda_de_texto_libre_en_titulo_y_descripcion(auth_client, pqr):
    respuesta = auth_client.get("/api/pqr", {"q": "certificado"})
    radicados = [item["radicado"] for item in respuesta.data["results"]]
    assert pqr.radicado in radicados

    respuesta_sin_match = auth_client.get("/api/pqr", {"q": "palabraquenoexiste"})
    assert respuesta_sin_match.data["count"] == 0


def test_exportar_csv_requiere_autenticacion(api_client):
    respuesta = api_client.get("/api/pqr/exportar")
    assert respuesta.status_code == 401


def test_exportar_csv_incluye_la_pqr(auth_client, pqr):
    respuesta = auth_client.get("/api/pqr/exportar")

    assert respuesta.status_code == 200
    assert respuesta["Content-Type"] == "text/csv"
    contenido = respuesta.content.decode("utf-8")
    assert pqr.radicado in contenido


def test_calificar_pqr_cerrada_es_publico(api_client, pqr):
    pqr.estado = PQR.Estado.CERRADA
    pqr.save(update_fields=["estado"])

    respuesta = api_client.post(
        "/api/pqr/calificar",
        {"radicado": pqr.radicado, "calificacion": 5, "comentario": "Excelente atención."},
        format="json",
    )

    assert respuesta.status_code == 200
    pqr.refresh_from_db()
    assert pqr.calificacion == 5
    assert pqr.comentario_calificacion == "Excelente atención."


def test_calificar_pqr_no_cerrada_es_rechazado(api_client, pqr):
    respuesta = api_client.post(
        "/api/pqr/calificar",
        {"radicado": pqr.radicado, "calificacion": 5},
        format="json",
    )
    assert respuesta.status_code == 400


def test_no_se_puede_calificar_dos_veces(api_client, pqr):
    pqr.estado = PQR.Estado.CERRADA
    pqr.calificacion = 4
    pqr.save(update_fields=["estado", "calificacion"])

    respuesta = api_client.post(
        "/api/pqr/calificar",
        {"radicado": pqr.radicado, "calificacion": 1},
        format="json",
    )
    assert respuesta.status_code == 400


def test_estadisticas_incluye_vencidas_por_vencer_y_calificacion(auth_client, pqr):
    pqr.estado = PQR.Estado.CERRADA
    pqr.calificacion = 5
    pqr.save(update_fields=["estado", "calificacion"])

    respuesta = auth_client.get("/api/estadisticas")

    assert respuesta.status_code == 200
    assert "vencidas" in respuesta.data
    assert "por_vencer" in respuesta.data
    assert respuesta.data["calificacion_promedio"] == 5.0
