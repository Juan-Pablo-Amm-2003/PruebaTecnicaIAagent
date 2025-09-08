from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
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

# CORS (ajustá orígenes reales si hace falta)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://tu-frontend.com"],
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
    # UX mínima: redirigí a la documentación interactiva
    return RedirectResponse(url="/docs", status_code=307)

# Health genérico (para compatibilidad con frontends existentes)
@app.get("/health")
async def health(settings: Settings = Depends(get_settings)):
    return {
        "app": settings.app_name,
        "debug": settings.debug,
        "azure_deployment": settings.azure_openai_deployment,
    }

# Liveness: ¿el proceso responde?
@app.get("/health/live")
async def health_live():
    return {"status": "ok"}

# Readiness: ¿está listo para servir tráfico? (check rápido del agente/modelo)
@app.get("/health/ready")
async def health_ready():
    try:
        agent = get_agent()
        # Ping corto. Si falla, devolvemos 503 para que el orquestador no enrute tráfico.
        _ = agent.run("ping")
        return {"ready": True}
    except Exception as e:
        log.error("readiness_failed", error=str(e))
        raise HTTPException(status_code=503, detail="not ready")

# Chequeo explícito a Azure (diagnóstico)
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

        # Normalización del resultado (Agno puede devolver obj o str)
        text = reply.text if hasattr(reply, "text") else (reply if isinstance(reply, str) else str(reply))
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
