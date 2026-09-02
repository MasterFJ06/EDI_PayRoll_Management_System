from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.persistence.models.user import User


class UserRepository:
    """Repository for User persistence operations."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, user_id: int) -> User | None:
        statement = select(User).where(User.user_id == user_id)
        return self.session.scalar(statement)

    def get_by_username(self, username: str) -> User | None:
        statement = select(User).where(User.username == username)
        return self.session.scalar(statement)

    def get_by_email(self, email: str) -> User | None:
        statement = select(User).where(User.email == email)
        return self.session.scalar(statement)

    def add(self, user: User) -> User:
        self.session.add(user)
        self.session.flush()
        return user