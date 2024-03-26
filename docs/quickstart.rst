Quickstart
********************

Logging and metrics
==================================

.. code-block:: python

    import logging

    from asgi_monitor.integrations.fastapi import MetricsConfig, setup_metrics
    from asgi_monitor.logging import configure_logging
    from asgi_monitor.logging.uvicorn import build_uvicorn_log_config
    from fastapi import FastAPI
    from uvicorn import run

    logger = logging.getLogger(__name__)
    app = FastAPI(debug=True)


    def run_app() -> None:
        log_config = build_uvicorn_log_config(level=logging.INFO, json_format=True, include_trace=False)
        metrics_config = MetricsConfig(app_name="fastapi")

        configure_logging(level=logging.INFO, json_format=True, include_trace=False)
        setup_metrics(app, metrics_config)

        logger.info("App is ready to start")

        run(app, host="127.0.0.1", port=8000, log_config=log_config)


    if __name__ == "__main__":
        run_app()


In this example, all logs will be presented in JSON format and the following metrics will be set for the application:

1. ``fastapi_app_info`` - ASGI application information (Gauge)
2. ``fastapi_requests_total`` - Total count of requests by method and path (Counter)
3. ``fastapi_responses_total`` - Total count of responses by method, path and status codes (Counter)
4. ``fastapi_request_duration_seconds`` - Histogram of request duration by path, in seconds (Histogram)
5. ``fastapi_requests_in_progress`` - Gauge of requests by method and path currently being processed (Gauge)
6. ``fastapi_requests_exceptions_total`` - Total count of exceptions raised by path and exception type (Counter)

You can also set up a global ``REGISTRY`` in ``MetricsConfig`` to support your **global** metrics,
but it is better to use your own non-global registry or leave the default registry

.. code-block:: python

    from prometheus_client import REGISTRY
    from asgi_monitor.integrations.fastapi import MetricsConfig

    metrics_config = MetricsConfig(app_name="fastapi", registry=REGISTRY)


And these metrics are available by endpoint ``/metrics``,
but you can import ``get_latest_metrics`` from ``asgi_monitor.metrics`` to create a custom endpoint.
