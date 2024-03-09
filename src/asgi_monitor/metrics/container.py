# https://github.com/litestar-org/litestar/blob/main/litestar/contrib/prometheus/middleware.py

from __future__ import annotations

from typing import ClassVar, cast

from prometheus_client import Counter, Gauge, Histogram, metrics

__all__ = ("MetricsContainer",)


class MetricsContainer:
    """Prometheus's metrics container"""

    _metrics: ClassVar[dict[str, metrics.MetricWrapperBase]] = {}

    def __init__(self, prefix: str = "asgi") -> None:
        self._prefix = prefix

    def app_info(self) -> Gauge:
        metric_name = f"{self._prefix}_app_info"

        if metric_name not in self._metrics:
            self._metrics[metric_name] = Gauge(
                name=metric_name,
                documentation="ASGI application information",
                labelnames=["app_name"],
            )
        return cast("Gauge", self._metrics[metric_name])

    def request_count(self) -> Counter:
        metric_name = f"{self._prefix}_requests_total"

        if metric_name not in self._metrics:
            self._metrics[metric_name] = Counter(
                name=metric_name,
                documentation="Total count of requests by method and path",
                labelnames=["app_name", "method", "path"],
            )
        return cast("Counter", self._metrics[metric_name])

    def response_count(self) -> Counter:
        metric_name = f"{self._prefix}_responses_total"

        if metric_name not in self._metrics:
            self._metrics[metric_name] = Counter(
                name=metric_name,
                documentation="Total count of responses by method, path and status codes",
                labelnames=["app_name", "method", "path", "status_code"],
            )
        return cast("Counter", self._metrics[metric_name])

    def request_duration(self) -> Histogram:
        metric_name = f"{self._prefix}_request_duration_seconds"

        if metric_name not in self._metrics:
            self._metrics[metric_name] = Histogram(
                name=metric_name,
                documentation="Histogram of request duration by path, in seconds",
                labelnames=["app_name", "method", "path"],
            )
        return cast("Histogram", self._metrics[metric_name])

    def requests_in_progress(self) -> Gauge:
        metric_name = f"{self._prefix}_requests_in_progress"

        if metric_name not in self._metrics:
            self._metrics[metric_name] = Gauge(
                name=metric_name,
                documentation="Gauge of requests by method and path currently being processed",
                labelnames=["app_name", "method", "path"],
                multiprocess_mode="livesum",
            )
        return cast("Gauge", self._metrics[metric_name])

    def requests_exceptions_count(self) -> Counter:
        metric_name = f"{self._prefix}_requests_exceptions_total"

        if metric_name not in self._metrics:
            self._metrics[metric_name] = Counter(
                name=metric_name,
                documentation="Total count of exceptions raised by path and exception type",
                labelnames=["app_name", "method", "path", "exception_type"],
            )
        return cast("Counter", self._metrics[metric_name])
