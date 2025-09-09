# 📘 Agno + FastAPI + Azure AI Foundry — Backend

Servicio REST en **FastAPI** que expone un **Agente Agno** en `/agent/invoke`, con **health checks** y **métricas Prometheus**. Listo para desarrollo local y despliegue en contenedores.

---

## 🚀 Requisitos

```txt
- Python 3.12+
- Docker Engine / Docker Desktop (opcional)
- Credenciales Azure AI Foundry/OpenAI:
  - AZURE_OPENAI_ENDPOINT
  - AZURE_OPENAI_API_KEY
  - AZURE_OPENAI_API_VERSION
  - AZURE_OPENAI_DEPLOYMENT
```

---

## ⚙️ Configuración

`.env` (ejemplo):

```env
APP_NAME=pruebatecnicasancorseguros
DEBUG=false

AZURE_OPENAI_ENDPOINT=https://<tu-resource>.openai.azure.com
AZURE_OPENAI_API_KEY=<tu_api_key>
AZURE_OPENAI_API_VERSION=2024-08-01-preview
AZURE_OPENAI_DEPLOYMENT=gpt-4.1

# Orígenes permitidos para CORS (separados por comas)
CORS_ORIGINS=http://localhost:3000,https://tu-frontend.com
```

👉 Crear a partir del template:

```bash
cp .env.example .env
```

---

## 💻 Desarrollo local

```bash
python -m venv .venv
# Windows
.\.venv\Scripts\Activate.ps1
# Linux/Mac
source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

👉 Abrir: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🐳 Docker (desarrollo)

`docker-compose.dev.yml`

```yaml
version: "3.9"
services:
  api:
    build: .
    image: agno-fastapi-azure:dev
    container_name: agno-fastapi-azure-dev
    env_file:
      - .env
    ports:
      - "8080:8000"
    command: >
      uvicorn app.main:app
      --host 0.0.0.0
      --port 8000
      --reload
    volumes:
      - ./:/app
    environment:
      WATCHFILES_FORCE_POLLING: "1"
```

Correr:

```bash
docker compose -f docker-compose.dev.yml up --build
```

👉 UI: [http://localhost:8080/docs](http://localhost:8080/docs)

---

## 🏭 Producción

`Dockerfile` (simplificado):

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -U pip && pip install -r requirements.txt

COPY . .

# Instalar curl para healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD curl -fsS http://localhost:8000/health/live || exit 1

# Default: Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Opción recomendada: Gunicorn + UvicornWorker

`gunicorn.conf.py`

```python
import multiprocessing

bind = "0.0.0.0:8000"
workers = max(2, multiprocessing.cpu_count() // 2)
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 120
keepalive = 5
```

Ejecutar:

```bash
gunicorn -k uvicorn.workers.UvicornWorker app.main:app -w 2 -b 0.0.0.0:8000
```

---

## 📡 Endpoints

```txt
GET /              → redirect /docs
GET /docs          → Swagger UI
GET /health/live   → proceso arriba
GET /health/ready  → dependencias OK
GET /health/azure  → chequeo Azure
GET /metrics       → métricas Prometheus
POST /agent/invoke → invocar agente
```

---

## 🔗 Ejemplo de invocación

```bash
curl -X POST http://localhost:8000/agent/invoke \
  -H "Content-Type: application/json" \
  -d '{ "message": "ping", "temperature": 0.2 }'
```



