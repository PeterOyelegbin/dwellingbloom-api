# Stage 1: Builder - Install dependencies
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --upgrade pip && pip install --prefix=/install -r requirements.txt

# Stage 2: Runtime - Production image
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    PORT=8000 DJANGO_SETTINGS_MODULE=core.settings \
    SERVER_MODE=web

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl && rm -rf /var/lib/apt/lists/* \
    && groupadd --system djangoUser && useradd --system --gid djangoUser djangoUser

COPY --from=builder /install /usr/local
COPY . .

RUN mkdir -p /app/staticfiles /app/media && chown -R djangoUser:djangoUser /app

USER djangoUser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -fsS http://127.0.0.1:${PORT}/health/ || exit 1

CMD ["sh", "-c", "if [ \"${SERVER_MODE}\" = \"worker\" ]; then exec celery -A core worker -l info -Q default,emails; elif [ \"${SERVER_MODE}\" = \"asgi\" ]; then exec uvicorn --host 0.0.0.0 --port ${PORT} --workers 2 core.asgi:application; else exec gunicorn --bind 0.0.0.0:${PORT} --workers 2 --worker-class gthread --threads 4 core.wsgi:application; fi"]
