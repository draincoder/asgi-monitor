from .config import BaseMetricsConfig
from .container import MetricsContainer

__all__ = (
    "MetricsManager",
    "build_metrics_manager",
)


class MetricsManager:
    __slots__ = ("_app_name", "_container")

    def __init__(self, app_name: str, container: MetricsContainer) -> None:
        self._app_name = app_name
        self._container = container

    def add_app_info(self) -> None:
        self._container.app_info().labels(app_name=self._app_name).inc()

    def inc_requests_count(
        self,
        method: str,
        path: str,
    ) -> None:
        self._container.request_count().labels(
            app_name=self._app_name,
            method=method,
            path=path,
        ).inc()

    def inc_responses_count(
        self,
        method: str,
        path: str,
        status_code: int | str,
    ) -> None:
        self._container.response_count().labels(
            app_name=self._app_name,
            method=method,
            path=path,
            status_code=status_code,
        ).inc()

    def observe_request_duration(
        self,
        method: str,
        path: str,
        duration: float,
        exemplar: dict[str, str] | None,
    ) -> None:
        self._container.request_duration().labels(
            app_name=self._app_name,
            method=method,
            path=path,
        ).observe(
            amount=duration,
            exemplar=exemplar,
        )

    def add_request_in_progress(
        self,
        method: str,
        path: str,
    ) -> None:
        self._container.requests_in_progress().labels(
            app_name=self._app_name,
            method=method,
            path=path,
        ).inc()

    def remove_request_in_progress(
        self,
        method: str,
        path: str,
    ) -> None:
        self._container.requests_in_progress().labels(
            app_name=self._app_name,
            method=method,
            path=path,
        ).dec()

    def inc_requests_exceptions_count(
        self,
        method: str,
        path: str,
        exception_type: str,
    ) -> None:
        self._container.requests_exceptions_count().labels(
            app_name=self._app_name,
            method=method,
            path=path,
            exception_type=exception_type,
        ).inc()


def build_metrics_manager(config: BaseMetricsConfig) -> MetricsManager:
    container = MetricsContainer(config.metrics_prefix, config.registry)
    return MetricsManager(app_name=config.app_name, container=container)
