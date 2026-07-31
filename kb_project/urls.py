"""Root URL configuration."""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("kbapp.urls")),
    path("api/", include("kbapp.api_urls")),
]
