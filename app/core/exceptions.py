import logging

from fastapi import Request
from fastapi.responses import JSONResponse

from app.domain.shared.exceptions import (
    BusinessRuleViolation,
    DomainError,
    InvalidDomainState,
)


logger = logging.getLogger(__name__)


def get_request_id(request: Request) -> str:
    return getattr(
        request.state,
        "request_id",
        "-",
    )

async def business_rule_violation_handler(
    request: Request,
    exc: BusinessRuleViolation,
) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={
            "error": {
                "code": "BUSINESS_RULE_VIOLATION",
                "message": str(exc),
                "request_id": get_request_id(request),
            }
        },
    )

async def invalid_domain_state_handler(
    request: Request,
    exc: InvalidDomainState,
) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={
            "error": {
                "code": "INVALID_DOMAIN_STATE",
                "message": str(exc),
                "request_id": get_request_id(request),
            }
        },
    )

async def domain_error_handler(
    request: Request,
    exc: DomainError,
) -> JSONResponse:
    logger.warning(
        "Unhandled domain error: %s",
        exc,
    )

    return JSONResponse(
        status_code=400,
        content={
            "error": {
                "code": "DOMAIN_ERROR",
                "message": str(exc),
                "request_id": get_request_id(request),
            }
        },
    )

async def unexpected_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    logger.exception(
        "Unhandled application exception",
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred.",
                "request_id": get_request_id(request),
            }
        },
    )