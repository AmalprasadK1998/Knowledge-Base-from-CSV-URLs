"""DRF serializers for the REST API."""
from __future__ import annotations

from rest_framework import serializers

from .models import ContentChunk, HarvestedURL


class ContentChunkSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentChunk
        fields = ["chunk_index", "text", "token_count"]


class HarvestedURLSerializer(serializers.ModelSerializer):
    """Serializer exposing all harvested metadata + raw content."""

    chunks = serializers.SerializerMethodField()

    class Meta:
        model = HarvestedURL
        fields = [
            "id",
            "url",
            "source_file",
            "http_status",
            "status",
            "title",
            "meta_description",
            "raw_html",
            "extracted_text",
            "content_hash",
            "error_message",
            "chunks",
            "created_at",
            "updated_at",
        ]

    def get_chunks(self, obj):
        return ContentChunkSerializer(obj.chunks.all(), many=True).data
