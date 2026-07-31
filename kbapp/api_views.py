"""DRF views for the REST API."""
from __future__ import annotations

from rest_framework import viewsets

from .models import HarvestedURL
from .serializers import HarvestedURLSerializer


class HarvestedURLViewSet(viewsets.ReadOnlyModelViewSet):
    """GET /api/urls/ — list harvested URLs with status, raw HTML, metadata."""

    queryset = HarvestedURL.objects.prefetch_related("chunks").all()
    serializer_class = HarvestedURLSerializer
    lookup_field = "id"
