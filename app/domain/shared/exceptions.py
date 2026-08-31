class DomainError(Exception):
    """Base exception for domain rule violations."""


class BusinessRuleViolation(DomainError):
    """Raised when a domain business rule is violated."""


class InvalidDomainState(DomainError):
    """Raised when an entity would enter an invalid state."""