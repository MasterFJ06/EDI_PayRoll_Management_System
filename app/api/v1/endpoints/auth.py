from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.application.common.unit_of_work import UnitOfWork
from app.application.identity.schemas import (
    UserLoginRequest,
    UserLoginResponse,
    UserRegistrationRequest,
    UserRegistrationResponse,
    RefreshTokenRequest,
    TokenPairResponse,
)
from app.application.identity.refresh_token_service import RefreshTokenService
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
        refresh_token=RefreshTokenService(uow).issue(user),
        token_type="bearer",
    )


@router.post("/refresh", response_model=TokenPairResponse)
def refresh_tokens(
    request: RefreshTokenRequest,
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> TokenPairResponse:
    pair = RefreshTokenService(uow).rotate(request.refresh_token)
    if pair is None:
        raise _invalid_refresh_credential()
    return TokenPairResponse(
        access_token=create_access_token(pair.user.user_id, pair.user.username),
        refresh_token=pair.refresh_token,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: RefreshTokenRequest,
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> Response:
    if not RefreshTokenService(uow).logout(request.refresh_token):
        raise _invalid_refresh_credential()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _invalid_refresh_credential() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token.",
        headers={"WWW-Authenticate": "Bearer"},
    )
