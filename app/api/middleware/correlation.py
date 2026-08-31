import logging
import time
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.logging import request_id_context


logger = logging.getLogger(__name__)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Assign a unique request ID to each HTTP request."""

    async def dispatch(
        self,
        request: Request,
        call_next,
    ) -> Response:
        request_id = str(uuid4())

        token = request_id_context.set(request_id)

        request.state.request_id = request_id

        start_time = time.perf_counter()

        try:
            logger.info(
                "Request started method=%s path=%s",
                request.method,
                request.url.path,
            )

            response = await call_next(request)

            duration_ms = (
                time.perf_counter() - start_time
            ) * 1000

            response.headers["X-Request-ID"] = request_id

            logger.info(
                "Request completed method=%s path=%s "
                "status_code=%s duration_ms=%.2f",
                request.method,
                request.url.path,
                response.status_code,
                duration_ms,
            )

            return response

        finally:
            request_id_context.reset(token)