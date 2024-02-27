import pytest

from asgi_monitor.metrics._container import MetricsContainer


@pytest.fixture(scope="session")
def container() -> MetricsContainer:
    return MetricsContainer(prefix="test")


@pytest.fixture(autouse=True)
def _clear_metrics(container: MetricsContainer) -> None:
    for metric in container._metrics.values():
        metric.clear()
