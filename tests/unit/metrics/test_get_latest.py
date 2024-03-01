import os
from multiprocessing import Process
from pathlib import Path

from assertpy import assert_that
from dirty_equals import IsBytes

from asgi_monitor.metrics import get_latest_metrics
from asgi_monitor.metrics.get_latest import MetricsResponse
from asgi_monitor.metrics.manager import MetricsManager


def test_get_latest_openmetrics_false(manager: MetricsManager) -> None:
    # Arrange
    expected = MetricsResponse(
        status_code=200,
        headers={"Content-Type": "text/plain; version=0.0.4; charset=utf-8"},
        payload=IsBytes,
    )
    manager.add_app_info()
    manager.add_request_in_progress(method="GET", path="/metrics/")

    # Act
    response = get_latest_metrics(openmetrics_format=False)

    # Assert
    assert_that(response).is_equal_to(expected)
    assert_that(response.payload.decode()).contains(
        'test_requests_in_progress{app_name="asgi-monitor",method="GET",path="/metrics/"} 1.0',
        'test_app_info{app_name="asgi-monitor"} 1.0',
    )


def test_get_latest_openmetrics_true(manager: MetricsManager) -> None:
    # Arrange
    expected = MetricsResponse(
        status_code=200,
        headers={"Content-Type": "application/openmetrics-text; version=1.0.0; charset=utf-8"},
        payload=IsBytes,
    )
    manager.add_app_info()
    manager.add_request_in_progress(method="GET", path="/metrics/")

    # Act
    response = get_latest_metrics(openmetrics_format=True)

    # Assert
    assert_that(response).is_equal_to(expected)
    assert_that(response.payload.decode()).contains(
        'test_requests_in_progress{app_name="asgi-monitor",method="GET",path="/metrics/"} 1.0',
        'test_app_info{app_name="asgi-monitor"} 1.0',
    )


def add_metrics(manager: MetricsManager) -> None:
    manager.inc_requests_count(method="GET", path="/metrics/")
    manager.inc_requests_count(method="GET", path="/token/")
    manager.inc_requests_count(method="GET", path="/login/")


def test_get_latest_metrics_multiprocess(tmpdir: Path, manager: MetricsManager) -> None:
    # Arrange
    os.environ["PROMETHEUS_MULTIPROC_DIR"] = str(tmpdir)
    processes = [Process(target=add_metrics, args=(manager,)) for _ in range(10)]

    for process in processes:
        process.start()

    for process in processes:
        process.join()

    expected = MetricsResponse(
        status_code=200,
        headers={"Content-Type": "text/plain; version=0.0.4; charset=utf-8"},
        payload=IsBytes,
    )

    # Act
    response = get_latest_metrics(openmetrics_format=False)

    # Assert
    assert_that(response).is_equal_to(expected)
    assert_that(response.payload.decode()).contains(
        'test_requests_total{app_name="asgi-monitor",method="GET",path="/metrics/"} 10.0',
        'test_requests_total{app_name="asgi-monitor",method="GET",path="/token/"} 10.0',
        'test_requests_total{app_name="asgi-monitor",method="GET",path="/login/"} 10.0',
    )
