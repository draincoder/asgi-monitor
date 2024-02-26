import logging
from collections.abc import Iterator

import pytest
import structlog

ROOT_LOGGER = logging.getLogger()


@pytest.fixture(autouse=True)
def _ensure_logging_framework_not_altered() -> Iterator[None]:
    """
    Prevents 'ValueError: I/O operation on closed file.' errors.
    """
    before_handlers = list(ROOT_LOGGER.handlers)

    yield

    ROOT_LOGGER.handlers = before_handlers


@pytest.fixture(autouse=True)
def _reset_structlog_configuration() -> Iterator[None]:
    assert structlog.is_configured() is False
    structlog.reset_defaults()

    yield

    structlog.reset_defaults()
    assert structlog.is_configured() is False


@pytest.fixture(autouse=True)
def _reset_logging_configuration() -> Iterator[None]:
    logging.basicConfig(handlers=[], force=True, level=logging.NOTSET)

    yield

    logging.basicConfig(handlers=[], force=True, level=logging.NOTSET)
