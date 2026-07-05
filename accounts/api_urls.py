from rest_framework.routers import DefaultRouter

from .views import UsuarioViewSet

router = DefaultRouter(trailing_slash=False)
router.register("usuarios", UsuarioViewSet, basename="usuarios")

urlpatterns = router.urls
