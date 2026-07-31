"""Admin registrations for the kbapp models."""
from django.contrib import admin

from .models import ContentChunk, HarvestedURL


class ContentChunkInline(admin.TabularInline):
    model = ContentChunk
    extra = 0
    readonly_fields = ("chunk_index", "token_count", "text")


@admin.register(HarvestedURL)
class HarvestedURLAdmin(admin.ModelAdmin):
    list_display = ("url", "status", "http_status", "title", "created_at")
    list_filter = ("status",)
    search_fields = ("url", "title", "meta_description")
    readonly_fields = ("content_hash", "created_at", "updated_at")
    inlines = [ContentChunkInline]
