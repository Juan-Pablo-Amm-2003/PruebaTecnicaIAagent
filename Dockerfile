# ===== Stage 1: builder =====
FROM python:3.12-slim AS builder

WORKDIR /app
ENV VIRTUAL_ENV=/opt/venv
RUN python -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Herramientas mínimas para compilar wheels si hace falta
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential ca-certificates && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -U pip && pip install --no-cache-dir -r requirements.txt

# ===== Stage 2: runtime =====
FROM python:3.12-slim AS runtime

# Utilidad para healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Usuario no root
RUN useradd -m -u 10001 appuser
WORKDIR /app

# Traemos el venv del builder
ENV VIRTUAL_ENV=/opt/venv
COPY --from=builder $VIRTUAL_ENV $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Copiamos código y ajustamos ownership
COPY . .
RUN chown -R appuser:appuser /app

# Flags Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Puerto parametrizable por PaaS
ENV PORT=8000
EXPOSE 8000

USER appuser

# Healthcheck (liveness)
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD curl -fsS "http://127.0.0.1:${PORT}/health/live" || exit 1

# Uvicorn por defecto (respeta $PORT)
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
