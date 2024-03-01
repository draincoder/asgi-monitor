import logging
from datetime import datetime, timedelta, timezone

import structlog
from _pytest.capture import CaptureFixture
from assertpy import assert_that

from asgi_monitor.logging import configure_logging
from tests.unit.logging.utils import capture_full_logs, read_json_logs


def test_simple_log(capfd: CaptureFixture) -> None:
    # Arrange
    configure_logging(json_format=True)
    logger = structlog.get_logger("testlogger")

    # Act
    logger.info("simple message")

    # Assert
    [simple_log] = read_json_logs(capfd)

    assert_that(simple_log).is_equal_to(
        {
            "event": "simple message",
            "filename": "test_default_json.py",
            "func_name": "test_simple_log",
            "level": "info",
            "logger": "testlogger",
            "module": "test_default_json",
            "thread_name": "MainThread",
        },
        ignore=["timestamp", "thread", "process", "pathname", "process_name"],
    )
    assert_that(simple_log).contains_key(
        "timestamp",
        "thread",
        "process",
        "pathname",
        "process_name",
    )


def test_kwargs_log(capfd: CaptureFixture) -> None:
    # Arrange
    configure_logging(json_format=True)
    logger = structlog.get_logger("testlogger")

    # Act
    logger.info(
        "kwargs message",
        test_int=123,
        test_str="params",
        test_dict={"key": "value"},
    )

    # Assert
    [kwargs_log] = read_json_logs(capfd)

    assert_that(kwargs_log).is_equal_to(
        {
            "event": "kwargs message",
            "filename": "test_default_json.py",
            "func_name": "test_kwargs_log",
            "level": "info",
            "logger": "testlogger",
            "module": "test_default_json",
            "test_dict": {"key": "value"},
            "test_int": 123,
            "test_str": "params",
            "thread_name": "MainThread",
        },
        ignore=["timestamp", "thread", "process", "pathname", "process_name"],
    )
    assert_that(kwargs_log).contains_key(
        "timestamp",
        "thread",
        "process",
        "pathname",
        "process_name",
    )


def test_timestamp_format(capfd: CaptureFixture) -> None:
    # Arrange
    configure_logging(json_format=True)
    logger = structlog.get_logger()

    # Act
    with capture_full_logs() as cap_logs:
        logger.info("simple message")

    # Assert
    [simple_log] = cap_logs

    now = datetime.now(tz=timezone.utc)
    raw_timestamp = simple_log["timestamp"]
    timestamp = datetime.strptime(raw_timestamp, "%Y-%m-%d %H:%M:%S.%f").replace(tzinfo=timezone.utc)

    assert_that(timestamp).is_close_to(now, timedelta(seconds=2))


def test_filter_logs_by_level(capfd: CaptureFixture) -> None:
    # Arrange
    configure_logging(level=logging.WARNING, json_format=True)
    logger = structlog.get_logger("testlogger")

    # Act
    logger.debug("debug message")
    logger.info("info message")
    logger.warning("warning message")
    logger.error("error message")

    # Assert
    messages = read_json_logs(capfd)

    assert_that(messages).extracting("level").contains_only("warning", "error")
