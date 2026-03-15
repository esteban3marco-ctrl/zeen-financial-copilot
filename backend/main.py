"""FastAPI application entrypoint for the Financial Copilot demo."""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

# Load .env early so ANTHROPIC_API_KEY and other vars are in os.environ
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"), override=True)
except ImportError:
    pass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import get_settings
from backend.routers import chat, demo, health, sessions
from backend.websocket.handler import router as ws_router

logger = logging.getLogger(__name__)


def _setup_telemetry(endpoint: str) -> None:
    """Configure OpenTelemetry OTLP exporter if endpoint is provided."""
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource = Resource.create({"service.name": "staq-zeen-backend", "service.version": "1.0.0"})
        provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)

        # Instrument FastAPI
        try:
            from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
            FastAPIInstrumentor().instrument()
        except ImportError:
            logger.debug("opentelemetry-instrumentation-fastapi not installed — skipping auto-instrumentation")

        logger.info("OpenTelemetry configured: endpoint=%s", endpoint)
    except ImportError:
        logger.warning("opentelemetry packages not installed — telemetry disabled")
    except Exception as exc:
        logger.error("Failed to configure OpenTelemetry: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: startup and shutdown hooks."""
    settings = get_settings()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    )

    # OpenTelemetry setup
    if settings.OPENTELEMETRY_ENDPOINT:
        _setup_telemetry(settings.OPENTELEMETRY_ENDPOINT)

    # Bootstrap MCP tool registry
    try:
        from tools.registry import get_registry
        from backend.services.registry_bootstrap import bootstrap_registry

        registry = await get_registry()
        await bootstrap_registry(registry)
        logger.info("MCP tool registry bootstrapped")
    except ImportError:
        logger.warning("tools.registry not available — skipping registry bootstrap")
    except Exception as exc:
        logger.error("Registry bootstrap failed: %s", exc)

    logger.info(
        "Staq/Zeen Financial Copilot backend ready — demo_mode=%s model=%s",
        settings.DEMO_MODE,
        settings.LLM_MODEL,
    )

    yield

    logger.info("Staq/Zeen backend shutting down")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Staq/Zeen Financial Copilot",
        description=(
            "FastAPI backend for the Staq/Zeen Financial Copilot demo. "
            "Demonstrates the 4-layer OPA risk gate framework with LangGraph."
        ),
        version="1.0.0",
        docs_url="/docs" if settings.DEMO_MODE else None,
        redoc_url="/redoc" if settings.DEMO_MODE else None,
        lifespan=lifespan,
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    if settings.DEMO_MODE:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    else:
        # Production: restrict to explicit origins
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[settings.SUPABASE_URL] if settings.SUPABASE_URL else [],
            allow_credentials=True,
            allow_methods=["GET", "POST", "DELETE"],
            allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        )

    # ── Routers ───────────────────────────────────────────────────────────────
    app.include_router(health.router, prefix="/api")
    app.include_router(chat.router, prefix="/api")
    app.include_router(sessions.router, prefix="/api")
    app.include_router(demo.router, prefix="/api")
    app.include_router(ws_router)

    @app.get("/", include_in_schema=False)
    async def root() -> dict[str, Any]:
        return {
            "service": "staq-zeen-backend",
            "version": "1.0.0",
            "demo_mode": settings.DEMO_MODE,
            "docs": "/docs" if settings.DEMO_MODE else None,
        }

    return app


app = create_app()
