import pytest
from prometheus_client import REGISTRY


@pytest.fixture(autouse=True)
def _reset_registry() -> None:
    collectors = tuple(REGISTRY._collector_to_names.keys())
    for collector in collectors:
        try:
            collector._metrics.clear()
            collector._metric_init()
        except AttributeError:
            pass
