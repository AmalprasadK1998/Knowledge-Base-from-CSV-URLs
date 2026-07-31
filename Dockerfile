# Build stage: install dependencies with uv into a virtualenv.
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy

# Install uv.
RUN pip install --no-cache-dir uv

WORKDIR /app

# Copy only manifests first for better layer caching.
COPY pyproject.toml ./
COPY README.md ./

# Install the project (and its dependencies) into a virtualenv.
RUN uv venv /app/.venv && \
    uv pip install --python /app/.venv/bin/python -e ".[embeddings]"

# --- Runtime stage ---------------------------------------------------------
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=kb_project.settings \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Copy the virtualenv from the builder and the source code.
COPY --from=builder /app/.venv /app/.venv
COPY . .

# Create a non-root user for safety.
RUN useradd -m appuser && chown -R appuser /app
USER appuser

EXPOSE 8000

# Collect static files and run gunicorn.
ENTRYPOINT ["sh", "-c", "python manage.py migrate --noinput && python manage.py collectstatic --noinput && exec python manage.py runserver 0.0.0.0:8000"]
