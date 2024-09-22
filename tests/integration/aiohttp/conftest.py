from aiohttp.test_utils import TestClient
from aiohttp.web import Application

from asgi_monitor.integrations.aiohttp import MetricsConfig, TracingConfig, setup_metrics, setup_tracing


def aiohttp_app() -> Application:
    app = Application()

    metrics_cfg = MetricsConfig()
    trace_cfg = TracingConfig()

    setup_metrics(app)
    setup_tracing(app)


async def test_cli(aiohttp_client: TestClient) -> TestClient:
    pass
