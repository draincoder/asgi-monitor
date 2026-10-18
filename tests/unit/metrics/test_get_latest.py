import multiprocessing
import os
from multiprocessing import Process
from pathlib import Path

import pytest
from assertpy import assert_that
from dirty_equals import IsBytes
from prometheus_client import CollectorRegistry, Counter

from asgi_monitor.metrics import get_latest_metrics
from asgi_monitor.metrics.config import _build_default_registry
from asgi_monitor.metrics.container import MetricsContainer
from asgi_monitor.metrics.get_latest import MetricsResponse
from asgi_monitor.metrics.manager import MetricsManager


def test_get_latest_openmetrics_false(manager: MetricsManager) -> None:
    # Arrange
    expected = MetricsResponse(
        status_code=200,
        headers={"Content-Type": "text/plain; version=0.0.4; charset=utf-8"},
        payload=IsBytes,  # type: ignore[arg-type]
    )
    manager.add_app_info()
    manager.add_request_in_progress(method="GET", path="/metrics")

    # Act
    response = get_latest_metrics(manager._container._registry, openmetrics_format=False)

    # Assert
    assert_that(response).is_equal_to(expected)
    assert_that(response.payload.decode()).contains(
        'test_requests_in_progress{app_name="asgi-monitor",method="GET",path="/metrics"} 1.0',
        'test_app_info{app_name="asgi-monitor"} 1.0',
    )


def test_get_latest_openmetrics_true(manager: MetricsManager) -> None:
    # Arrange
    expected = MetricsResponse(
        status_code=200,
        headers={"Content-Type": "application/openmetrics-text; version=1.0.0; charset=utf-8"},
        payload=IsBytes,  # type: ignore[arg-type]
    )
    manager.add_app_info()
    manager.add_request_in_progress(method="GET", path="/metrics")

    # Act
    response = get_latest_metrics(manager._container._registry, openmetrics_format=True)

    # Assert
    assert_that(response).is_equal_to(expected)
    assert_that(response.payload.decode()).contains(
        'test_requests_in_progress{app_name="asgi-monitor",method="GET",path="/metrics"} 1.0',
        'test_app_info{app_name="asgi-monitor"} 1.0',
    )


def add_metrics() -> None:
    manager = MetricsManager(
        app_name="asgi-monitor",
        container=MetricsContainer("test", _build_default_registry()),
    )

    for _ in range(10):
        manager.inc_requests_count(method="GET", path="/metrics")
        manager.inc_requests_count(method="GET", path="/token")
        manager.inc_requests_count(method="GET", path="/login")


def test_get_latest_metrics_multiprocess(tmpdir: Path, manager: MetricsManager) -> None:
    # Arrange
    multiprocessing.set_start_method("spawn", force=True)
    os.environ["PROMETHEUS_MULTIPROC_DIR"] = str(tmpdir)
    processes = [Process(target=add_metrics) for _ in range(10)]

    for process in processes:
        process.start()

    for process in processes:
        process.join()

    expected = MetricsResponse(
        status_code=200,
        headers={"Content-Type": "text/plain; version=0.0.4; charset=utf-8"},
        payload=IsBytes,  # type: ignore[arg-type]
    )

    # Act
    response = get_latest_metrics(manager._container._registry, openmetrics_format=False)

    # Assert
    assert_that(response).is_equal_to(expected)
    assert_that(response.payload.decode()).contains(
        'test_requests_total{app_name="asgi-monitor",method="GET",path="/metrics"} 100.0',
        'test_requests_total{app_name="asgi-monitor",method="GET",path="/token"} 100.0',
        'test_requests_total{app_name="asgi-monitor",method="GET",path="/login"} 100.0',
    )


@pytest.mark.parametrize("accept_header", ["", "*/*", "text/plain; version=0.0.4", "application/json"])
def test_prometheus_format_fallback(accept_header: str) -> None:
    # Arrange
    registry = CollectorRegistry()
    counter = Counter("requests", "Requests", registry=registry)
    counter.inc()

    # Act
    response = get_latest_metrics(registry, openmetrics_format=False, accept_header=accept_header)

    # Assert
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "text/plain; version=0.0.4; charset=utf-8"
    assert b"requests_total 1.0\n" in response.payload
    assert not response.payload.endswith(b"# EOF\n")


@pytest.mark.parametrize(
    ("openmetrics_format", "accept_header"),
    [
        (False, "application/openmetrics-text; version=1.0.0"),
        (True, "text/plain; version=0.0.4"),
    ],
)
def test_openmetrics_exemplars(*, openmetrics_format: bool, accept_header: str) -> None:
    # Arrange
    registry = CollectorRegistry()
    counter = Counter("requests", "Requests", registry=registry)
    counter.inc(exemplar={"trace_id": "abc123"})

    # Act
    response = get_latest_metrics(registry, openmetrics_format=openmetrics_format, accept_header=accept_header)

    # Assert
    assert response.status_code == 200
    assert response.headers["Content-Type"] in {
        "application/openmetrics-text; version=1.0.0; charset=utf-8",
        "application/openmetrics-text; version=1.0.0; charset=utf-8; escaping=underscores",
    }
    assert b'requests_total 1.0 # {trace_id="abc123"} 1.0' in response.payload
    assert response.payload.endswith(b"# EOF\n")
