import logging

from _pytest.capture import CaptureFixture
from assertpy import assert_that
from fastapi import FastAPI
from httpx import AsyncClient
from uvicorn import Config

from asgi_monitor.integrations.fastapi import setup_tracing
from asgi_monitor.logging import configure_logging
from asgi_monitor.logging.uvicorn import build_uvicorn_log_config
from tests.integration.utils import build_fastapi_tracing_config, run_server
from tests.utils import read_console_logs, read_json_logs


async def test_uvicorn_logs_format_json(capfd: CaptureFixture) -> None:
    # Arrange
    configure_logging(level=logging.INFO, json_format=True)

    log_config = build_uvicorn_log_config(level=logging.INFO, json_format=True, include_trace=False)
    app = FastAPI()
    config = Config(app=app, log_config=log_config)

    # Act
    async with run_server(config):
        pass

    # Assert
    logs = read_json_logs(capfd)
    started_log, *head = logs

    assert started_log["event"].startswith("Started server process [")
    assert_that(head).extracting("event").is_equal_to(
        [
            "Waiting for application startup.",
            "Application startup complete.",
            "Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)",
            "Shutting down",
            "Waiting for application shutdown.",
            "Application shutdown complete.",
        ],
    )
    assert_that(logs).extracting("logger").contains_only("uvicorn.error")
    assert_that(logs).extracting("thread_name").contains_only("MainThread")
    assert_that(logs).extracting("process_name").contains_only("MainProcess")

    for log in logs:
        assert_that(log).contains_key(
            "event",
            "filename",
            "module",
            "func_name",
            "timestamp",
            "thread",
            "process",
            "pathname",
        )


async def test_uvicorn_logs_format_console(capfd: CaptureFixture) -> None:
    # Arrange
    configure_logging(level=logging.INFO, json_format=False)

    log_config = build_uvicorn_log_config(level=logging.INFO, json_format=False, include_trace=False)
    app = FastAPI()
    config = Config(app=app, log_config=log_config)

    # Act
    async with run_server(config):
        pass

    # Assert
    logs = read_console_logs(capfd)
    started_log, *head = logs

    assert_that(started_log).contains("Started server process [")
    assert_that("\n".join(head)).contains(
        "Waiting for application startup.",
        "Application startup complete.",
        "Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)",
        "Shutting down",
        "Waiting for application shutdown.",
        "Application shutdown complete.",
    )

    for log in logs:
        assert_that(log).contains(
            "uvicorn.error",
            "thread_name",
            "MainThread",
            "process_name",
            "MainProcess",
            "filename",
            "module",
            "func_name",
            "thread",
            "process",
            "pathname",
        )


async def test_uvicorn_logs_with_trace_format_console(capfd: CaptureFixture) -> None:
    # Arrange
    trace_config, _ = build_fastapi_tracing_config()
    app = FastAPI()

    setup_tracing(app, trace_config)
    configure_logging(level=logging.INFO, json_format=False)

    log_config = build_uvicorn_log_config(level=logging.INFO, json_format=False, include_trace=True)
    config = Config(app=app, log_config=log_config)

    # Act
    async with run_server(config), AsyncClient() as client:
        await client.get("http://127.0.0.1:8000")

    # Assert
    logs = read_console_logs(capfd)
    request_log = logs[4]
    assert_that(request_log).contains(
        "client_addr",
        "uvicorn.access",
        "thread_name",
        "MainThread",
        "process_name",
        "MainProcess",
        "filename",
        "module",
        "func_name",
        "thread",
        "process",
        "pathname",
        "parent_span_id",
        "service.name",
        "trace_id",
        "span_id",
    )


async def test_uvicorn_logs_with_trace_format_json(capfd: CaptureFixture) -> None:
    # Arrange
    trace_config, _ = build_fastapi_tracing_config()
    app = FastAPI()

    setup_tracing(app, trace_config)
    configure_logging(level=logging.INFO, json_format=True)

    log_config = build_uvicorn_log_config(level=logging.INFO, json_format=True, include_trace=True)
    config = Config(app=app, log_config=log_config)

    # Act
    async with run_server(config), AsyncClient() as client:
        await client.get("http://127.0.0.1:8000")

    # Assert
    logs = read_json_logs(capfd)
    request_log = logs[4]
    assert_that([request_log]).extracting("service.name").contains_only("fastapi")
    assert_that(request_log).contains_key(
        "event",
        "filename",
        "module",
        "func_name",
        "timestamp",
        "thread",
        "process",
        "pathname",
        "parent_span_id",
        "service.name",
        "trace_id",
        "span_id",
    )
