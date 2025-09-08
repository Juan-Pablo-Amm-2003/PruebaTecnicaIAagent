# ===== Stage 1: builder (instala deps en un venv) =====
FROM python:3.12-slim AS builder

WORKDIR /app
ENV VIRTUAL_ENV=/opt/venv
RUN python -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Dependencias del sistema (compilación ligera + runtime SSL/CA)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Copiamos requirements primero para cachear la capa de deps
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ===== Stage 2: runtime (no-root, imagen mínima) =====
FROM python:3.12-slim AS runtime

# Crear usuario no root
RUN useradd -m -u 10001 appuser

WORKDIR /app

# Copiamos el venv ya armado desde el builder
ENV VIRTUAL_ENV=/opt/venv
COPY --from=builder $VIRTUAL_ENV $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Copiamos el código (respetando .dockerignore)
COPY . .

# Seguridad básica
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Puerto (overridable por env/Compose)
ENV PORT=8000
EXPOSE 8000

# Usuario no-root
USER appuser

# Healthcheck sencillo contra /health
HEALTHCHECK --interval=30s --timeout=3s --retries=3 CMD curl -fsS http://127.0.0.1:${PORT}/health || exit 1

# Comando default: Uvicorn 1 worker (Azure/Render suelen requerirlo)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]


# Exponer puerto
EXPOSE 8000

# HEALTHCHECK del contenedor (usa liveness)
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD wget -qO- http://127.0.0.1:8000/health/live || exit 1
