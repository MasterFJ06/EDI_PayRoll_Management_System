from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.middleware.correlation import CorrelationIdMiddleware
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import (
    business_rule_violation_handler,
    domain_error_handler,
    invalid_domain_state_handler,
    unexpected_exception_handler,
)
from app.core.logging import configure_logging
from app.domain.shared.exceptions import (
    BusinessRuleViolation,
    DomainError,
    InvalidDomainState,
)


configure_logging()

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown lifecycle."""

    yield


def create_application() -> FastAPI:
    application = FastAPI(
        title="Employee Payroll Management System API",
        version="1.0.0",
        description=(
            "Backend API for employee information, attendance, leave, "
            "compensation, payroll processing, and audit management."
        ),
        lifespan=lifespan,
    )

    allowed_origins = [
        origin.strip()
        for origin in settings.cors_origins.split(",")
        if origin.strip()
    ]

    application.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.add_middleware(
        CorrelationIdMiddleware,
    )

    application.add_exception_handler(
        BusinessRuleViolation,
        business_rule_violation_handler,
    )

    application.add_exception_handler(
        InvalidDomainState,
        invalid_domain_state_handler,
    )

    application.add_exception_handler(
        DomainError,
        domain_error_handler,
    )

    application.add_exception_handler(
        Exception,
        unexpected_exception_handler,
    )

    application.include_router(
        api_router,
        prefix="/api/v1",
    )

    return application


app = create_application()