from app.application.common.unit_of_work import UnitOfWork


class AuthorizationService:
    """Application-level access to the current persisted permission state."""

    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def has_permission(self, user_id: int, permission_code: str) -> bool:
        if self.uow.authorization is None:
            raise RuntimeError("Unit of Work has not been started.")
        return self.uow.authorization.has_permission(user_id, permission_code)
