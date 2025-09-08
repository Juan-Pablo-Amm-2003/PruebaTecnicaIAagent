import logging
import sys
import structlog


def configure_logging(level: str = "INFO") -> None:
    timestamper = structlog.processors.TimeStamper(fmt="iso")
    processors = [
        structlog.contextvars.merge_contextvars,
        timestamper,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),  # Logs JSON-friendly
    ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, level, logging.INFO)),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )

    # Integrar logging stdlib -> structlog
    logging.basicConfig(level=getattr(logging, level, logging.INFO), stream=sys.stdout)
    for noisy in ("uvicorn.access", "uvicorn.error", "httpx", "asyncio"):
        logging.getLogger(noisy).setLevel(logging.INFO)
