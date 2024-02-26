import structlog
from _pytest.capture import CaptureFixture
from assertpy import assert_that

from asgi_monitor.logging import configure_logging
from tests.logging.utils import read_console_logs


def test_simple_log(capfd: CaptureFixture) -> None:
    # Arrange
    configure_logging(json_format=False)
    logger = structlog.get_logger("testlogger")

    # Act
    logger.info("simple message")

    # Assert
    simple_log = read_console_logs(capfd)[0]

    assert_that(simple_log).contains(
        "info",
        "simple message",
        "testlogger",
        "filename",
        "test_default_console.py",
        "func_name",
        "test_simple_log",
        "module",
        "test_default_console",
        "thread_name",
        "MainThread",
        "thread",
        "process",
        "pathname",
        "process_name",
    )


def test_kwargs_log(capfd: CaptureFixture) -> None:
    # Arrange
    configure_logging(json_format=False)
    logger = structlog.get_logger("testlogger")

    # Act
    logger.info(
        "kwargs message",
        test_int=123,
        test_str="params",
        test_dict={"key": "value"},
    )

    # Assert
    kwargs_log = read_console_logs(capfd)[0]

    assert_that(kwargs_log).contains(
        "info",
        "kwargs message",
        "testlogger",
        "filename",
        "test_default_console.py",
        "func_name",
        "test_kwargs_log",
        "module",
        "test_default_console",
        "thread_name",
        "MainThread",
        "test_dict",
        "{'key': 'value'}",
        "test_int",
        "123",
        "test_str",
        "params",
        "thread",
        "process",
        "pathname",
        "process_name",
    )
