from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.api.dependencies.current_user import get_current_user
from app.api.dependencies.unit_of_work import get_unit_of_work
from app.application.common.unit_of_work import UnitOfWork
from app.application.identity.schemas import (
    UserLoginRequest,
    UserLoginResponse,
    UserMeResponse,
    UserRegistrationRequest,
    UserRegistrationResponse,
)
from app.application.identity.user_service import UserService
from app.infrastructure.persistence.models.user import User
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

    user_me = service.to_user_me(user)

    return UserLoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=user_me,
    )


@router.get(
    "/me",
    response_model=UserMeResponse,
)
def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> UserMeResponse:
    service = UserService(uow)
    return service.to_user_me(current_user)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
)
def logout_user() -> Response:
    return Response(status_code=status.HTTP_204_NO_CONTENT)