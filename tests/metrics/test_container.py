import time
from datetime import datetime, timezone

from assertpy import assert_that
from dirty_equals import IsStr
from freezegun import freeze_time
from prometheus_client.metrics import Exemplar, Metric, Sample

from asgi_monitor.metrics._container import MetricsContainer

APP_NAME = "asgi-monitor"


def test_app_info(container: MetricsContainer) -> None:
    # Arrange
    expected = Metric(
        name="test_app_info",
        documentation="ASGI application information",
        unit="",
        typ="gauge",
    )
    expected.samples = [
        Sample(
            name="test_app_info",
            labels={"app_name": "asgi-monitor"},
            value=1.0,
            timestamp=None,
            exemplar=None,
        ),
    ]

    # Act
    container.app_info().labels(app_name=APP_NAME).inc()

    # Assert
    app_info = container.app_info().collect()
    assert_that(app_info).is_equal_to([expected])


@freeze_time(datetime(year=2024, month=2, day=28, hour=0, minute=40, second=50, tzinfo=timezone.utc))
def test_request_count(container: MetricsContainer) -> None:
    # Arrange
    expected = Metric(
        name="test_requests",
        documentation="Total count of requests by method and path",
        unit="",
        typ="counter",
    )
    expected.samples = [
        Sample(
            name="test_requests_total",
            labels={"app_name": "asgi-monitor", "method": "GET", "path": "/metrics/"},
            value=1.0,
            timestamp=None,
            exemplar=None,
        ),
        Sample(
            name="test_requests_created",
            labels={"app_name": "asgi-monitor", "method": "GET", "path": "/metrics/"},
            value=1709080850.0,
            timestamp=None,
            exemplar=None,
        ),
    ]

    # Act
    container.request_count().labels(app_name=APP_NAME, method="GET", path="/metrics/").inc()

    # Assert
    request_count = container.request_count().collect()
    assert_that(request_count).is_equal_to([expected])


@freeze_time(datetime(year=2024, month=2, day=28, hour=0, minute=40, second=50, tzinfo=timezone.utc))
def test_response_count(container: MetricsContainer) -> None:
    # Arrange
    expected = Metric(
        name="test_responses",
        documentation="Total count of responses by method, path and status codes",
        unit="",
        typ="counter",
    )
    expected.samples = [
        Sample(
            name="test_responses_total",
            labels={"app_name": "asgi-monitor", "method": "GET", "path": "/metrics/", "status_code": "200"},
            value=1.0,
            timestamp=None,
            exemplar=None,
        ),
        Sample(
            name="test_responses_created",
            labels={"app_name": "asgi-monitor", "method": "GET", "path": "/metrics/", "status_code": "200"},
            value=1709080850.0,
            timestamp=None,
            exemplar=None,
        ),
    ]

    # Act
    container.response_count().labels(app_name=APP_NAME, method="GET", path="/metrics/", status_code=200).inc()

    # Assert
    response_count = container.response_count().collect()
    assert_that(response_count).is_equal_to([expected])


@freeze_time(datetime(year=2024, month=2, day=28, hour=0, minute=40, second=50, tzinfo=timezone.utc))
def test_request_duration(container: MetricsContainer) -> None:
    # Arrange
    expected = (
        "test_request_duration_seconds",
        "Histogram of request duration by path, in seconds",
        "histogram",
        "",
    )
    expected_sample_bucket_with_exemplar = Sample(
        name="test_request_duration_seconds_bucket",
        labels={"app_name": "asgi-monitor", "method": "GET", "path": "/metrics/", "le": IsStr},
        value=1.0,
        timestamp=None,
        exemplar=Exemplar(labels={"TraceID": "1234567"}, value=0.0, timestamp=1709080850.0),
    )
    expected_sample_bucket_without_exemplar = Sample(
        name="test_request_duration_seconds_bucket",
        labels={"app_name": "asgi-monitor", "method": "GET", "path": "/metrics/", "le": IsStr},
        value=1.0,
        timestamp=None,
        exemplar=None,
    )
    expected_sample_count = Sample(
        name="test_request_duration_seconds_count",
        labels={"app_name": "asgi-monitor", "method": "GET", "path": "/metrics/"},
        value=1.0,
        timestamp=None,
        exemplar=None,
    )
    expected_sample_sum = Sample(
        name="test_request_duration_seconds_sum",
        labels={"app_name": "asgi-monitor", "method": "GET", "path": "/metrics/"},
        value=0.0,
        timestamp=None,
        exemplar=None,
    )
    expected_sample_created = Sample(
        name="test_request_duration_seconds_created",
        labels={"app_name": "asgi-monitor", "method": "GET", "path": "/metrics/"},
        value=1709080850.0,
        timestamp=None,
        exemplar=None,
    )

    after_time = time.perf_counter()
    before_time = time.perf_counter()

    # Act
    container.request_duration().labels(
        app_name=APP_NAME,
        method="GET",
        path="/metrics/",
    ).observe(
        after_time - before_time,
        exemplar={"TraceID": "1234567"},
    )

    # Assert
    request_duration = container.request_duration().collect()
    samples = request_duration[0].samples

    assert_that(request_duration).extracting("name", "documentation", "type", "unit").is_equal_to([expected])
    assert_that(samples[0]).is_equal_to(expected_sample_bucket_with_exemplar)
    assert_that(samples[1]).is_equal_to(expected_sample_bucket_without_exemplar)
    assert_that(samples[-3]).is_equal_to(expected_sample_count)
    assert_that(samples[-2]).is_equal_to(expected_sample_sum)
    assert_that(samples[-1]).is_equal_to(expected_sample_created)

    for sample in samples[2:-3]:
        assert_that(sample).is_equal_to(expected_sample_bucket_without_exemplar)


def test_requests_in_progress_inc(container: MetricsContainer) -> None:
    # Arrange
    expected = Metric(
        name="test_requests_in_progress",
        documentation="Gauge of requests by method and path currently being processed",
        unit="",
        typ="gauge",
    )
    expected.samples = [
        Sample(
            name="test_requests_in_progress",
            labels={"app_name": "asgi-monitor", "method": "GET", "path": "/metrics/"},
            value=1.0,
            timestamp=None,
            exemplar=None,
        ),
    ]

    # Act
    container.requests_in_progress().labels(app_name=APP_NAME, method="GET", path="/metrics/").inc()

    # Assert
    requests_in_progress = container.requests_in_progress().collect()
    assert_that(requests_in_progress).is_equal_to([expected])


def test_requests_in_progress_dec(container: MetricsContainer) -> None:
    # Arrange
    expected = Metric(
        name="test_requests_in_progress",
        documentation="Gauge of requests by method and path currently being processed",
        unit="",
        typ="gauge",
    )
    expected.samples = [
        Sample(
            name="test_requests_in_progress",
            labels={"app_name": "asgi-monitor", "method": "GET", "path": "/metrics/"},
            value=0.0,
            timestamp=None,
            exemplar=None,
        ),
    ]

    # Act
    container.requests_in_progress().labels(app_name=APP_NAME, method="GET", path="/metrics/").inc()
    container.requests_in_progress().labels(app_name=APP_NAME, method="GET", path="/metrics/").dec()

    # Assert
    requests_in_progress = container.requests_in_progress().collect()
    assert_that(requests_in_progress).is_equal_to([expected])


@freeze_time(datetime(year=2024, month=2, day=28, hour=0, minute=40, second=50, tzinfo=timezone.utc))
def test_requests_exceptions_count(container: MetricsContainer) -> None:
    # Arrange
    expected = Metric(
        name="test_requests_exceptions",
        documentation="Total count of exceptions raised by path and exception type",
        unit="",
        typ="counter",
    )
    expected.samples = [
        Sample(
            name="test_requests_exceptions_total",
            labels={"app_name": "asgi-monitor", "method": "GET", "path": "/metrics/", "exception_type": "RuntimeError"},
            value=1.0,
            timestamp=None,
            exemplar=None,
        ),
        Sample(
            name="test_requests_exceptions_created",
            labels={"app_name": "asgi-monitor", "method": "GET", "path": "/metrics/", "exception_type": "RuntimeError"},
            value=1709080850.0,
            timestamp=None,
            exemplar=None,
        ),
    ]

    # Act
    container.requests_exceptions_count().labels(
        app_name=APP_NAME,
        method="GET",
        path="/metrics/",
        exception_type=type(RuntimeError()).__name__,
    ).inc()

    # Assert
    requests_exceptions_count = container.requests_exceptions_count().collect()
    assert_that(requests_exceptions_count).is_equal_to([expected])
