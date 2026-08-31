import logging
from contextvars import ContextVar


request_id_context: ContextVar[str] = ContextVar(
    "request_id",
    default="-",
)

class RequestIdFilter(logging.Filter):
    """Inject the current request ID into log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_context.get()
        return True

def configure_logging() -> None:
    handler = logging.StreamHandler()

    handler.addFilter(RequestIdFilter())

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | "
        "%(name)s | request_id=%(request_id)s | %(message)s"
    )

    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    root_logger.handlers.clear()
    root_logger.addHandler(handler)