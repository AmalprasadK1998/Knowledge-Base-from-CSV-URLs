"""Web (HTML) URL routes (mounted at site root)."""
from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("search/", views.search, name="search"),
    path("urls/<int:pk>/", views.detail, name="detail"),
]
