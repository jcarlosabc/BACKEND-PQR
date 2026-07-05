import datetime

from django.conf import settings
from django.db import models
from django.utils import timezone

DIAS_SLA_RESPUESTA = getattr(settings, "PQR_DIAS_SLA", 15)


class Ciudadano(models.Model):
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    identificacion = models.CharField(max_length=20, unique=True)
    email = models.EmailField()
    telefono = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ciudadanos"
        ordering = ["apellido", "nombre"]

    def __str__(self):
        return f"{self.nombre} {self.apellido} ({self.identificacion})"

    @property
    def nombre_completo(self):
        return f"{self.nombre} {self.apellido}"


class PQR(models.Model):
    class Tipo(models.TextChoices):
        PETICION = "peticion", "Petición"
        QUEJA = "queja", "Queja"
        RECLAMO = "reclamo", "Reclamo"

    class Prioridad(models.TextChoices):
        BAJA = "baja", "Baja"
        MEDIA = "media", "Media"
        ALTA = "alta", "Alta"
        URGENTE = "urgente", "Urgente"

    class Estado(models.TextChoices):
        RECIBIDA = "recibida", "Recibida"
        EN_GESTION = "en_gestion", "En gestión"
        RESUELTA = "resuelta", "Resuelta"
        CERRADA = "cerrada", "Cerrada"

    class Canal(models.TextChoices):
        WEB = "web", "Web"
        EMAIL = "email", "Correo electrónico"
        PRESENCIAL = "presencial", "Presencial"

    TRANSICIONES_VALIDAS = {
        Estado.RECIBIDA: {Estado.EN_GESTION},
        Estado.EN_GESTION: {Estado.RESUELTA},
        Estado.RESUELTA: {Estado.CERRADA},
        Estado.CERRADA: set(),
    }

    radicado = models.CharField(max_length=20, unique=True, editable=False)
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    titulo = models.CharField(max_length=150)
    descripcion = models.TextField()
    categoria = models.CharField(max_length=60)
    prioridad = models.CharField(max_length=20, choices=Prioridad.choices, default=Prioridad.MEDIA)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.RECIBIDA)
    canal = models.CharField(max_length=20, choices=Canal.choices, default=Canal.WEB)

    solicitante = models.ForeignKey(Ciudadano, on_delete=models.PROTECT, related_name="pqrs")
    agente_asignado = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pqrs_asignadas",
    )

    fecha_limite = models.DateField(null=True, blank=True, editable=False)
    calificacion = models.PositiveSmallIntegerField(null=True, blank=True)
    comentario_calificacion = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "pqrs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["estado"]),
            models.Index(fields=["tipo"]),
            models.Index(fields=["prioridad"]),
        ]

    def __str__(self):
        return f"{self.radicado} — {self.titulo}"

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        if is_new and not self.fecha_limite:
            self.fecha_limite = timezone.now().date() + datetime.timedelta(days=DIAS_SLA_RESPUESTA)
        super().save(*args, **kwargs)
        if is_new and not self.radicado:
            year = timezone.now().year
            self.radicado = f"PQR-{year}-{self.id:06d}"
            super().save(update_fields=["radicado"])

    def transicion_valida(self, nuevo_estado):
        return nuevo_estado in self.TRANSICIONES_VALIDAS.get(self.estado, set())

    @property
    def sla_estado(self):
        """'a_tiempo' | 'por_vencer' (<=3 días) | 'vencida' | 'cumplido' | 'incumplido'.
        Los dos últimos aplican una vez la PQR está resuelta o cerrada."""
        if not self.fecha_limite:
            return "a_tiempo"
        if self.estado in (self.Estado.RESUELTA, self.Estado.CERRADA):
            return "cumplido" if self.updated_at.date() <= self.fecha_limite else "incumplido"
        dias_restantes = (self.fecha_limite - timezone.now().date()).days
        if dias_restantes < 0:
            return "vencida"
        if dias_restantes <= 3:
            return "por_vencer"
        return "a_tiempo"

    @property
    def puede_calificarse(self):
        return self.estado == self.Estado.CERRADA and self.calificacion is None


class Seguimiento(models.Model):
    class TipoAccion(models.TextChoices):
        COMENTARIO = "comentario", "Comentario interno"
        CAMBIO_ESTADO = "cambio_estado", "Cambio de estado"
        CAMBIO_PRIORIDAD = "cambio_prioridad", "Cambio de prioridad"
        ASIGNACION = "asignacion", "Asignación de agente"

    pqr = models.ForeignKey(PQR, on_delete=models.CASCADE, related_name="seguimientos")
    descripcion = models.TextField()
    tipo_accion = models.CharField(max_length=20, choices=TipoAccion.choices)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="seguimientos_registrados",
    )
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "seguimientos"
        ordering = ["fecha_registro"]

    def __str__(self):
        return f"Seguimiento de {self.pqr.radicado} — {self.tipo_accion}"
