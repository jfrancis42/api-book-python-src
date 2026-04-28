import logging
import time
import uuid
from contextvars import ContextVar

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from metrics import metrics

request_id_var: ContextVar[str] = ContextVar("request_id", default="")

log = logging.getLogger("api")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        incoming = request.headers.get("X-Correlation-Id")
        request_id = incoming if incoming else str(uuid.uuid4())[:8]
        request_id_var.set(request_id)

        start = time.monotonic()
        response = await call_next(request)
        duration_ms = int((time.monotonic() - start) * 1000)

        response.headers["X-Request-Id"] = request_id
        metrics.record(request.method, request.url.path, response.status_code, duration_ms)

        log.info(
            "request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": duration_ms,
                "client_ip": request.client.host if request.client else "-",
            },
        )
        return response
