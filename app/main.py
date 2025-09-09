from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
import os
import structlog

# --- imports internos ---
from app.core.settings import get_settings, Settings
from app.core.logging import configure_logging
from app.agent.agent import get_agent
from app.schemas import ChatRequest, ChatResponse

# --- métricas (degradación elegante) ---
try:
    from prometheus_fastapi_instrumentator import Instrumentator
    _METRICS_ENABLED = True
except Exception:
    Instrumentator = None  # type: ignore
    _METRICS_ENABLED = False

# ------------------------------------------------------------------------------
# Config app + logging
# ------------------------------------------------------------------------------
configure_logging()
log = structlog.get_logger()

app = FastAPI(title="Agno + FastAPI + Azure AI Foundry")

# === NUEVO: CORS configurable por env ===
# Permite lista separada por comas, con fallback seguro.
raw_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,https://tu-frontend.com")
allow_origins = [o.strip() for o in raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
)

# Prometheus /metrics (solo si la lib está instalada)
if _METRICS_ENABLED:
    Instrumentator().instrument(app).expose(app, endpoint="/metrics")

# ------------------------------------------------------------------------------
# Hooks de ciclo de vida
# ------------------------------------------------------------------------------
@app.on_event("startup")
async def on_startup():
    s = get_settings()
    log.info(
        "startup",
        app=s.app_name,
        debug=s.debug,
        deployment=s.azure_openai_deployment,
    )

# ------------------------------------------------------------------------------
# Rutas base
# ------------------------------------------------------------------------------
@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs", status_code=307)

@app.get("/health")
async def health(settings: Settings = Depends(get_settings)):
    return {
        "app": settings.app_name,
        "debug": settings.debug,
        "azure_deployment": settings.azure_openai_deployment,
    }

@app.get("/health/live")
async def health_live():
    return {"status": "ok"}

# === EDIT: readiness primero valida configuración antes de “pingear” el agente ===
@app.get("/health/ready")
async def health_ready(settings: Settings = Depends(get_settings)):
    try:
        # Validación rápida de config obligatoria
        if not (settings.azure_openai_endpoint and settings.azure_openai_api_key and settings.azure_openai_deployment):
            log.warning("readiness_config_missing")
            raise HTTPException(status_code=503, detail="missing azure configuration")

        agent = get_agent()
        # Ping corto. Si falla, 503 para que el LB/Orquestador no enrute tráfico.
        _ = agent.run("ping")
        return {"ready": True}
    except HTTPException:
        raise
    except Exception as e:
        log.error("readiness_failed", error=str(e))
        raise HTTPException(status_code=503, detail="not ready")

@app.get("/health/azure")
async def health_azure(settings: Settings = Depends(get_settings)):
    try:
        agent = get_agent()
        reply = agent.run("ping")
        text = reply.text if hasattr(reply, "text") else (reply if isinstance(reply, str) else str(reply))
        ok = isinstance(text, str) and len(text) > 0
        log.info("health_azure", ok=ok)
        return {"azure_ok": ok, "deployment": settings.azure_openai_deployment}
    except Exception as e:
        log.error("health_azure_error", error=str(e))
        raise HTTPException(status_code=502, detail=f"Azure check failed: {e}")

# ------------------------------------------------------------------------------
# Endpoint principal del agente
# ------------------------------------------------------------------------------
@app.post("/agent/invoke", response_model=ChatResponse)
async def invoke_agent(payload: ChatRequest):
    try:
        agent = get_agent()

        kwargs = {}
        if payload.temperature is not None:
            kwargs["temperature"] = payload.temperature
        if payload.max_tokens is not None:
            kwargs["max_tokens"] = payload.max_tokens
        if payload.top_p is not None:
            kwargs["top_p"] = payload.top_p

        reply = agent.run(payload.message, **kwargs)

        text = reply.text if hasattr(reply, "text") else (reply if isinstance(reply, "str") else str(reply))
        log.info("agent_invoke_ok", chars=len(text))
        return ChatResponse(
            reply=text,
            meta={"provider": "azure", "deployment": get_settings().azure_openai_deployment},
        )
    except HTTPException:
        raise
    except Exception as e:
        log.error("agent_invoke_error", error=str(e))
        raise HTTPException(status_code=502, detail=f"Error al invocar el agente de Azure: {e}")
