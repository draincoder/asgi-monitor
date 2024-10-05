import json
import logging

from _pytest.capture import CaptureFixture
from aiohttp.pytest_plugin import AiohttpClient, AiohttpRawServer
from aiohttp.web import Request, Response
from assertpy import assert_that
from opentelemetry import trace
from structlog import get_logger

from asgi_monitor.logging import configure_logging
from asgi_monitor.logging.aiohttp import TraceAccessLogger
from tests.integration.factory import build_aiohttp_tracing_config
from tests.utils import read_json_logs

logger = logging.getLogger(__name__)
struct_logger = get_logger(structlog_name="structlog")


async def log_in_controller(request: Request) -> Response:
    with trace.get_tracer("aiohttp").start_as_current_span("GET /") as span:
        if "log" in request.url.path:
            request.span = span

        struct_logger.info("trace info")

        with trace.get_tracer("aiohttp").start_as_current_span("test"):
            logger.info("trace error")

        return Response(body=json.dumps({"status": "ok"}))


async def test_aiohttp_logs_with_trace_in_controller_format_json(
    aiohttp_raw_server: AiohttpRawServer,
    aiohttp_client: AiohttpClient,
    capfd: CaptureFixture,
) -> None:
    # Arrange
    build_aiohttp_tracing_config()
    configure_logging(level=logging.INFO, json_format=True, include_trace=True)
    kwargs = {"access_log_class": TraceAccessLogger, "logger": logger}
    server = await aiohttp_raw_server(log_in_controller, **kwargs)  # type: ignore[arg-type]
    cli = await aiohttp_client(server)

    # Act
    await cli.get("/log")

    # Assert
    access_log = read_json_logs(capfd)[-1]
    assert_that(access_log).contains_key(
        "span_id",
        "trace_id",
        "service.name",
    )
    assert_that(access_log).does_not_contain_key("parent_span_id")


async def test_aiohttp_logs_with_trace_in_controller_format_json_parent(
    aiohttp_raw_server: AiohttpRawServer,
    aiohttp_client: AiohttpClient,
    capfd: CaptureFixture,
) -> None:
    # Arrange
    build_aiohttp_tracing_config()
    configure_logging(level=logging.INFO, json_format=True, include_trace=True)

    with trace.get_tracer("aiohttp").start_as_current_span("parent"):
        kwargs = {"access_log_class": TraceAccessLogger, "logger": logger}
        server = await aiohttp_raw_server(log_in_controller, **kwargs)  # type: ignore[arg-type]
        cli = await aiohttp_client(server)

        # Act
        await cli.get("/log")

    # Assert
    access_log = read_json_logs(capfd)[-1]
    assert_that(access_log).contains_key(
        "span_id",
        "trace_id",
        "service.name",
        "parent_span_id",
    )


async def test_aiohttp_logs_with_trace_in_controller_format_json_error(
    aiohttp_raw_server: AiohttpRawServer,
    aiohttp_client: AiohttpClient,
    capfd: CaptureFixture,
) -> None:
    # Arrange
    build_aiohttp_tracing_config()
    configure_logging(level=logging.INFO, json_format=True, include_trace=True)
    kwargs = {"access_log_class": TraceAccessLogger, "logger": logger}
    server = await aiohttp_raw_server(log_in_controller, **kwargs)  # type: ignore[arg-type]
    cli = await aiohttp_client(server)

    # Act
    await cli.get("/error")

    # Assert
    error_log = read_json_logs(capfd)[-1]
    assert_that(error_log).does_not_contain_key(
        "structlog_name",
        "span_id",
        "trace_id",
        "service.name",
    )


async def test_aiohttp_logs_with_trace_in_controller_format_json_critical_level(
    aiohttp_raw_server: AiohttpRawServer,
    aiohttp_client: AiohttpClient,
    capfd: CaptureFixture,
) -> None:
    # Arrange
    build_aiohttp_tracing_config()
    configure_logging(level=logging.CRITICAL, json_format=True, include_trace=True)
    kwargs = {"access_log_class": TraceAccessLogger, "logger": logger}
    server = await aiohttp_raw_server(log_in_controller, **kwargs)  # type: ignore[arg-type]
    cli = await aiohttp_client(server)

    # Act
    await cli.get("/log")

    # Assert
    out, _ = capfd.readouterr()
    assert len(out) == 0
