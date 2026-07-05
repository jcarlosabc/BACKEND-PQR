from django.conf import settings
from django.core.mail import send_mail


def notificar_creacion(pqr):
    send_mail(
        subject=f"PQR registrada — {pqr.radicado}",
        message=(
            f"Hola {pqr.solicitante.nombre},\n\n"
            f"Tu solicitud fue registrada con el radicado {pqr.radicado}.\n"
            f"Tipo: {pqr.get_tipo_display()}\n"
            f"Categoría: {pqr.categoria}\n\n"
            f"Puedes consultar el estado de tu solicitud en cualquier momento "
            f"usando este número de radicado.\n"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[pqr.solicitante.email],
        fail_silently=True,
    )


def notificar_cambio_estado(pqr):
    send_mail(
        subject=f"Actualización de tu PQR — {pqr.radicado}",
        message=(
            f"Hola {pqr.solicitante.nombre},\n\n"
            f"Tu solicitud {pqr.radicado} cambió de estado a: {pqr.get_estado_display()}.\n"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[pqr.solicitante.email],
        fail_silently=True,
    )
