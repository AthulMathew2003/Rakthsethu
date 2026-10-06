import logging
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.v1.router import v1_router
from app.core.config import settings
from app.core.exceptions import AppException
from app.core.middleware import RequestIdMiddleware, get_current_request_id
from app.core.response import error_response, success_response

logger = logging.getLogger("rakthasethu")

app = FastAPI(
    title="Rakthasethu API",
    description=(
        "Mission-critical Blood Donation Management and Donor-Matching Platform Backend. "
        "Provides RBAC authentication, hospital registry management, canonical donor records, "
        "donation ledgers, and clinical blood request tracking."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# 1. Request ID Middleware
app.add_middleware(RequestIdMiddleware)

# 2. CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)


# 3. Exception Handlers
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(
            message=exc.message,
            error_code=exc.error_code,
            details=exc.data,
        ),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = []
    for err in exc.errors():
        field = " -> ".join(str(loc) for loc in err.get("loc", []))
        errors.append({"field": field, "message": err.get("msg"), "type": err.get("type")})

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response(
            message="Request validation failed. Please check input parameters.",
            error_code="VALIDATION_ERROR",
            details=errors,
        ),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(
            message=str(exc.detail),
            error_code=f"HTTP_{exc.status_code}",
        ),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(f"Unhandled exception during request processing: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response(
            message="An unexpected internal server error occurred.",
            error_code="INTERNAL_SERVER_ERROR",
            details=str(exc) if settings.DEBUG else None,
        ),
    )


# 4. Health Check Endpoint
@app.get("/health", tags=["System Health"], summary="Health check endpoint")
async def health_check():
    """Returns application status and active request ID."""
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "env": settings.APP_ENV,
        "requestId": get_current_request_id(),
    }


# 5. Include Versioned v1 Router
app.include_router(v1_router)
