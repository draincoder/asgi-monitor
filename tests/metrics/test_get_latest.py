from assertpy import assert_that
from dirty_equals import IsBytes

from asgi_monitor.metrics import get_latest_metrics
from asgi_monitor.metrics.get_latest import MetricsResponse


def test_get_latest_openmetrics_false() -> None:
    # Arrange
    expected = MetricsResponse(
        status_code=200,
        headers={"Content-Type": "text/plain; version=0.0.4; charset=utf-8"},
        payload=IsBytes,
    )
    # Act
    response = get_latest_metrics(openmetrics_format=False)

    # Assert
    assert_that(response).is_equal_to(expected)


def test_get_latest_openmetrics_true() -> None:
    # Arrange
    expected = MetricsResponse(
        status_code=200,
        headers={"Content-Type": "application/openmetrics-text; version=1.0.0; charset=utf-8"},
        payload=IsBytes,
    )
    # Act
    response = get_latest_metrics(openmetrics_format=True)

    # Assert
    assert_that(response).is_equal_to(expected)
