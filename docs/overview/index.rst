Overview
********************

Wor what?
==================

For observe wev application

Installation
==================

.. code-block:: text

    pip install asgi-monitor

Example
==================

This is how the implementation of metrics in a FastAPI application looks like

.. code-block:: python

    import logging

    from asgi_monitor.integrations.fastapi import MetricsConfig, setup_metrics
    from fastapi import FastAPI
    from uvicorn import run

    logger = logging.getLogger(__name__)


    def run_app() -> None:
        app = FastAPI()
        metrics_config = MetricsConfig(app_name="fastapi")
        setup_metrics(app, metrics_config)
        run(app, host="127.0.0.1", port=8000, log_config=log_config)


    if __name__ == "__main__":
        run_app()

Dashboard
==================

.. image:: ../images/dashboard.png
   :alt: dashboard

Grafana dashboard.
