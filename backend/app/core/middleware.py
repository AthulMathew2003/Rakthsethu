import uuid
from contextvars import ContextVar
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Context variable to hold request_id for the lifetime of the request
request_id_ctx: ContextVar[str] = ContextVar("request_id_ctx", default="")


def get_current_request_id() -> str:
    """Retrieve current request ID from context, or generate one if not set."""
    rid = request_id_ctx.get()
    if not rid:
        rid = str(uuid.uuid4())
        request_id_ctx.set(rid)
    return rid


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Middleware that assigns a unique Request ID to each incoming HTTP request."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = request_id_ctx.set(request_id)
        try:
            response: Response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            request_id_ctx.reset(token)
