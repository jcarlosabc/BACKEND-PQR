from django.contrib import admin

from .models import PQR, Ciudadano, Seguimiento


class SeguimientoInline(admin.TabularInline):
    model = Seguimiento
    extra = 0
    readonly_fields = ["fecha_registro"]
    fields = ["tipo_accion", "descripcion", "usuario", "fecha_registro"]


@admin.register(PQR)
class PQRAdmin(admin.ModelAdmin):
    list_display = [
        "radicado",
        "titulo",
        "tipo",
        "estado",
        "prioridad",
        "solicitante",
        "created_at",
    ]
    list_filter = ["estado", "tipo", "prioridad", "canal"]
    search_fields = ["radicado", "titulo", "solicitante__nombre", "solicitante__apellido"]
    readonly_fields = ["radicado", "created_at", "updated_at"]
    inlines = [SeguimientoInline]


@admin.register(Ciudadano)
class CiudadanoAdmin(admin.ModelAdmin):
    list_display = ["nombre_completo", "identificacion", "email", "telefono"]
    search_fields = ["nombre", "apellido", "identificacion", "email"]


@admin.register(Seguimiento)
class SeguimientoAdmin(admin.ModelAdmin):
    list_display = ["pqr", "tipo_accion", "usuario", "fecha_registro"]
    list_filter = ["tipo_accion"]
