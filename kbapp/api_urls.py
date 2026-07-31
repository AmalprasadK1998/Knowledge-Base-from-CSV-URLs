"""REST API URL routes (mounted under /api/)."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .api_views import HarvestedURLViewSet

router = DefaultRouter()
router.register(r"urls", HarvestedURLViewSet, basename="harvestedurl")

urlpatterns = [
    path("", include(router.urls)),
]
