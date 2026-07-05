import django_filters
from django.db.models import Q
from django.utils import timezone

from .models import PQR


class PQRFilter(django_filters.FilterSet):
    categoria = django_filters.CharFilter(field_name="categoria", lookup_expr="iexact")
    q = django_filters.CharFilter(method="filtrar_texto_libre")
    vencidas = django_filters.BooleanFilter(method="filtrar_vencidas")

    class Meta:
        model = PQR
        fields = ["tipo", "estado", "prioridad", "categoria"]

    def filtrar_texto_libre(self, queryset, name, value):
        return queryset.filter(Q(titulo__icontains=value) | Q(descripcion__icontains=value))

    def filtrar_vencidas(self, queryset, name, value):
        abiertas = queryset.exclude(estado__in=[PQR.Estado.RESUELTA, PQR.Estado.CERRADA])
        if value:
            return abiertas.filter(fecha_limite__lt=timezone.now().date())
        return queryset
