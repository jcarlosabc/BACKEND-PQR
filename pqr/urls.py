from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import EstadisticasView, PQRViewSet

router = DefaultRouter(trailing_slash=False)
router.register("pqr", PQRViewSet, basename="pqr")

urlpatterns = [
    path("estadisticas", EstadisticasView.as_view(), name="estadisticas"),
    path("", include(router.urls)),
]
