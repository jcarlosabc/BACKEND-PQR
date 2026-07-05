from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import Usuario
from pqr.models import PQR, Ciudadano, Seguimiento

CIUDADANOS = [
    dict(
        nombre="Laura",
        apellido="Ramírez",
        identificacion="1010101010",
        email="laura.ramirez@example.com",
        telefono="3011234567",
    ),
    dict(
        nombre="Andrés",
        apellido="Molina",
        identificacion="1020202020",
        email="andres.molina@example.com",
        telefono="3022345678",
    ),
    dict(
        nombre="Sofía",
        apellido="Castro",
        identificacion="1030303030",
        email="sofia.castro@example.com",
        telefono="3033456789",
    ),
]

PQRS = [
    dict(
        tipo=PQR.Tipo.PETICION,
        titulo="Copia de historia clínica",
        descripcion="Solicito copia completa de mi historia clínica del último año.",
        categoria="historias_clinicas",
        prioridad=PQR.Prioridad.MEDIA,
        estado=PQR.Estado.RECIBIDA,
        canal=PQR.Canal.WEB,
    ),
    dict(
        tipo=PQR.Tipo.QUEJA,
        titulo="Demora en asignación de cita",
        descripcion="Llevo tres semanas esperando que me asignen cita con especialista.",
        categoria="citas_medicas",
        prioridad=PQR.Prioridad.ALTA,
        estado=PQR.Estado.EN_GESTION,
        canal=PQR.Canal.EMAIL,
    ),
    dict(
        tipo=PQR.Tipo.RECLAMO,
        titulo="Cobro duplicado de cuota moderadora",
        descripcion="En la factura de este mes aparece la cuota moderadora cobrada dos veces.",
        categoria="facturacion",
        prioridad=PQR.Prioridad.URGENTE,
        estado=PQR.Estado.RESUELTA,
        canal=PQR.Canal.PRESENCIAL,
    ),
    dict(
        tipo=PQR.Tipo.PETICION,
        titulo="Cambio de médico de cabecera",
        descripcion="Deseo cambiar mi médico de cabecera asignado por disponibilidad de horario.",
        categoria="afiliaciones",
        prioridad=PQR.Prioridad.BAJA,
        estado=PQR.Estado.CERRADA,
        canal=PQR.Canal.WEB,
    ),
]


class Command(BaseCommand):
    help = "Crea usuarios y PQR de ejemplo para probar el sistema localmente."

    @transaction.atomic
    def handle(self, *args, **options):
        self._crear_usuarios()
        self._crear_pqrs_demo()
        self.stdout.write(self.style.SUCCESS("Datos de ejemplo creados correctamente."))

    def _crear_usuarios(self):
        credenciales = [
            ("admin@sersocial.demo", "Admin1234!", "Administrador Demo", Usuario.Rol.ADMIN),
            (
                "supervisor@sersocial.demo",
                "Supervisor1234!",
                "Supervisora Demo",
                Usuario.Rol.SUPERVISOR,
            ),
            ("agente@sersocial.demo", "Agente1234!", "Agente Demo", Usuario.Rol.AGENTE),
        ]
        for email, password, nombre, rol in credenciales:
            if Usuario.objects.filter(email=email).exists():
                continue
            Usuario.objects.create_user(
                email=email,
                password=password,
                nombre=nombre,
                rol=rol,
                is_staff=(rol == Usuario.Rol.ADMIN),
                is_superuser=(rol == Usuario.Rol.ADMIN),
            )
            self.stdout.write(f"  usuario creado: {email} / {password}")

    def _crear_pqrs_demo(self):
        if PQR.objects.exists():
            self.stdout.write("  ya existen PQR, se omite la carga de ejemplo.")
            return

        agente = Usuario.objects.get(email="agente@sersocial.demo")
        ciudadanos = [Ciudadano.objects.create(**datos) for datos in CIUDADANOS]

        for i, datos in enumerate(PQRS):
            ciudadano = ciudadanos[i % len(ciudadanos)]
            pqr = PQR.objects.create(solicitante=ciudadano, **datos)
            if pqr.estado != PQR.Estado.RECIBIDA:
                Seguimiento.objects.create(
                    pqr=pqr,
                    descripcion=f"Estado inicial de ejemplo: {pqr.get_estado_display()}.",
                    tipo_accion=Seguimiento.TipoAccion.CAMBIO_ESTADO,
                    usuario=agente,
                )
