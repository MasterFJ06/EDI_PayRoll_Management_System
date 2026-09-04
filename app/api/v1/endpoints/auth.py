from typing import Annotated

from fastapi import APIRouter, Depends

from app.application.common.unit_of_work import UnitOfWork
from app.application.identity.schemas import (
    UserLoginRequest,
    UserLoginResponse,
    UserRegistrationRequest,
    UserRegistrationResponse,
)
from app.application.identity.user_service import UserService
from app.api.dependencies.unit_of_work import get_unit_of_work
from app.infrastructure.security.jwt import create_access_token

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post(
    "/register",
    response_model=UserRegistrationResponse,
    status_code=201,
)
def register_user(
    request: UserRegistrationRequest,
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> UserRegistrationResponse:
    service = UserService(uow)

    return service.register(request)

@router.post(
    "/login",
    response_model=UserLoginResponse,
)
def login_user(
    request: UserLoginRequest,
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> UserLoginResponse:
    service = UserService(uow)

    user = service.authenticate(request)

    access_token = create_access_token(
        user_id=user.user_id,
        username=user.username,
    )

    return UserLoginResponse(
        access_token=access_token,
        token_type="bearer",
    )