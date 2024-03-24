import os

import pytest

from asgi_monitor.metrics.config import _build_default_registry
from asgi_monitor.metrics.container import MetricsContainer
from asgi_monitor.metrics.manager import MetricsManager


@pytest.fixture(scope="session")
def container() -> MetricsContainer:
    return MetricsContainer(prefix="test", registry=_build_default_registry())


@pytest.fixture(scope="session")
def manager(container: MetricsContainer) -> MetricsManager:
    return MetricsManager(app_name="asgi-monitor", container=container)


@pytest.fixture(autouse=True)
def _clear_metrics(container: MetricsContainer) -> None:
    for metric in container._metrics.values():
        metric.clear()


@pytest.fixture(autouse=True)
def _clear_env() -> None:
    os.environ.pop("PROMETHEUS_MULTIPROC_DIR", None)
