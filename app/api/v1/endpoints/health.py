from fastapi import APIRouter


router = APIRouter()


@router.get("/health", tags=["Health"])
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "employee-payroll-api",
    }