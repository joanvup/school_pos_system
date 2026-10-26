"""Logging estructurado en JSON con identificador de petición.

No registra cuerpos, cabeceras ni query strings: solo método, plantilla de ruta,
estado y duración, para no filtrar datos personales ni secretos.
"""

import json
import logging
import re
import time
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")

REQUEST_LOGGER = "app.request"
_HEALTH_ROUTE = "/health"
_MAX_ROUTE_LEN = 200


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", None) or request_id_ctx.get(),
        }
        for field in ("method", "route", "status", "duration_ms"):
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(level: int = logging.INFO) -> None:
    """Instala el formateador JSON una sola vez, sin pisar los de gunicorn."""
    root = logging.getLogger()
    if any(getattr(handler, "_school_pos_json", False) for handler in root.handlers):
        return
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    handler._school_pos_json = True  # type: ignore[attr-defined]
    root.addHandler(handler)
    root.setLevel(level)


def _route(request: Request) -> str:
    route = request.scope.get("route")
    template = getattr(route, "path", None)
    if not template:
        return request.url.path[:_MAX_ROUTE_LEN]

    # FastAPI anida los routers incluidos: la ruta solo trae su tramo final.
    # Reconstruimos el prefijo comparando la plantilla ya sustituida con la
    # ruta real, sin registrar nunca los valores dinámicos.
    actual = request.scope.get("path") or request.url.path
    path_params = request.scope.get("path_params") or {}
    rendered = template
    for name in re.findall(r"\{([^}]+)\}", template):
        key = name.split(":")[0]
        if key in path_params:
            rendered = re.sub(
                r"\{[^}]+\}", lambda _match: str(path_params[key]), rendered, count=1
            )
    if actual.endswith(rendered):
        template = actual[: len(actual) - len(rendered)] + template
    return template[:_MAX_ROUTE_LEN]


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Propaga un request id y registra cada petición de forma estructurada."""

    async def dispatch(self, request: Request, call_next):
        request_id = uuid.uuid4().hex[:16]
        token = request_id_ctx.set(request_id)
        started = time.perf_counter()
        response = None
        try:
            response = await call_next(request)
            return response
        except Exception:
            logging.getLogger(REQUEST_LOGGER).exception(
                "request_failed",
                extra={"method": request.method, "route": _route(request)},
            )
            raise
        finally:
            route = _route(request)
            status = response.status_code if response is not None else 500
            if route != _HEALTH_ROUTE:
                logging.getLogger(REQUEST_LOGGER).log(
                    logging.INFO if status < 500 else logging.WARNING,
                    "request",
                    extra={
                        "method": request.method,
                        "route": route,
                        "status": status,
                        "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                    },
                )
            if response is not None:
                response.headers["X-Request-ID"] = request_id
            request_id_ctx.reset(token)
