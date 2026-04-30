import json
import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Logs each HTTP request with method, path, status, and latency."""

    async def dispatch(self, request, call_next):
        request_id = uuid.uuid4().hex[:8]
        start = time.monotonic()
        response = await call_next(request)
        latency_ms = round((time.monotonic() - start) * 1000, 1)
        logger.info(json.dumps({
            "type": "http_request",
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "latency_ms": latency_ms,
        }))
        return response
