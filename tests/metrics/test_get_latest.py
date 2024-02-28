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
