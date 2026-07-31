"""Web (HTML) views: upload, harvest, search, detail."""
from __future__ import annotations

import logging

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.conf import settings

from .models import HarvestedURL
from .services.csv_parser import parse_csv
from .services.llm import synthesize_answer
from .services.pipeline import run_pipeline
from .services.vector_store import get_vector_store

logger = logging.getLogger(__name__)


def index(request):
    """Dashboard: upload form + recent harvested URLs."""
    if request.method == "POST" and request.FILES.get("csv_file"):
        return _handle_upload(request)

    recent = HarvestedURL.objects.all()[:25]
    store = get_vector_store()
    return render(
        request,
        "kbapp/index.html",
        {
            "recent": recent,
            "url_count": HarvestedURL.objects.count(),
            "chunk_count": _chunk_count(),
            "vector_count": store.size(),
        },
    )


def _handle_upload(request):
    upload = request.FILES["csv_file"]
    if not upload.name.lower().endswith(".csv"):
        messages.error(request, "Please upload a .csv file.")
        return redirect("index")

    data = upload.read()
    urls = parse_csv(data)
    if not urls:
        messages.error(request, "No URLs found in the uploaded CSV.")
        return redirect("index")

    logger.info("parsed %d urls from upload %s", len(urls), upload.name)
    summary = run_pipeline(urls, source_file=upload.name)
    messages.success(
        request,
        f"Processed {summary['urls']} URLs: {summary['scraped']} scraped, "
        f"{summary['failed']} failed. Vector index rebuilt.",
    )
    return redirect("index")


def search(request):
    """Semantic search interface."""
    query = request.GET.get("q", "").strip()
    hits = []
    answer = ""
    if query:
        store = get_vector_store()
        hits = store.search(query, top_k=settings.TOP_K)
        chunk_texts = [h.chunk_text for h in hits]
        answer = synthesize_answer(query, chunk_texts)
        logger.info("search '%s' -> %d hits", query, len(hits))
    return render(
        request,
        "kbapp/search.html",
        {"query": query, "hits": hits, "answer": answer},
    )


def detail(request, pk: int):
    """Detail view for a single harvested URL."""
    url_obj = get_object_or_404(HarvestedURL, pk=pk)
    return render(request, "kbapp/detail.html", {"url_obj": url_obj})


def _chunk_count() -> int:
    from .models import ContentChunk

    return ContentChunk.objects.count()
