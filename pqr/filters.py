import django_filters

from .models import PQR


class PQRFilter(django_filters.FilterSet):
    categoria = django_filters.CharFilter(field_name="categoria", lookup_expr="iexact")

    class Meta:
        model = PQR
        fields = ["tipo", "estado", "prioridad", "categoria"]
