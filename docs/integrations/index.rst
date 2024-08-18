.. _FastAPI: https://fastapi.tiangolo.com
.. _Starlette: https://www.starlette.io
.. _Litestar: https://litestar.dev
.. _real_world: https://github.com/draincoder/asgi-monitor/tree/master/examples/real_world

.. _integrations:

Integrations
*******************************

Integration with the following frameworks is **now** implemented:

* FastAPI_
* Starlette_
* Litestar_

But other integrations are planned in the near future, and you can also implement your own through **PR**.

FastAPI & Starlette
====================

These frameworks have the **same** integration api, so here I will show you how to configure monitoring for **FastAPI**.

.. code-block:: python
   :caption: Configuring monitoring for the FastAPI

   import logging

   from asgi_monitor.integrations.fastapi import MetricsConfig, TracingConfig, setup_metrics, setup_tracing
   from asgi_monitor.logging import configure_logging
   from asgi_monitor.logging.uvicorn import build_uvicorn_log_config
   from fastapi import APIRouter, FastAPI
   from opentelemetry import trace
   from opentelemetry.sdk.resources import Resource
   from opentelemetry.sdk.trace import TracerProvider
   import uvicorn



   def create_app() -> None:
       configure_logging(level=logging.INFO, json_format=True, include_trace=False)

       resource = Resource.create(
           attributes={
               "service.name": "fastapi",
           },
       )
       tracer_provider = TracerProvider(resource=resource)
       trace.set_tracer_provider(tracer_provider)

       trace_config = TracingConfig(tracer_provider=tracer_provider)
       metrics_config = MetricsConfig(app_name="fastapi", include_trace_exemplar=True)

       app = FastAPI()

       setup_metrics(app=app, config=metrics_config)
       setup_tracing(app=app, config=trace_config)  # Must be configured last

       return app


   if __name__ == "__main__":
      log_config = build_uvicorn_log_config(level=logging.INFO, json_format=True, include_trace=True)
      uvicorn.run(create_app(), host="127.0.0.1", port=8000, log_config=log_config)


For **Starlette**, simply replace ``fastapi`` with ``starlette`` in the **integration** import line.

Check out the real_world_ example to figure out how it works.


Litestar
====================

.. important::

   The API is incompatible with FastAPI and Starlette, the rules for determining the path are different, the type of error is not detected.

Litestar out of the box has many add-ons:

1. **Prometheus** support
2. **OpenTelemetry** support
3. **Structlog** plugin

But they all have disadvantages, for example, you can use only **global metrics** with a **global registry**, metrics are not compatible with the trace context, logs also do not support the trace context.

So **asgi-monitor** is rushing to the rescue.

.. code-block:: python
   :caption: Configuring monitoring for the Litestar

   import logging

   from asgi_monitor.integrations.litestar import (
       MetricsConfig,
       TracingConfig,
       add_metrics_endpoint,
       build_metrics_middleware,
       build_tracing_middleware,
   )
   from asgi_monitor.logging import configure_logging
   from asgi_monitor.logging.uvicorn import build_uvicorn_log_config
   from litestar import Litestar
   from opentelemetry import trace
   from opentelemetry.sdk.resources import Resource
   from opentelemetry.sdk.trace import TracerProvider
   import uvicorn

   logger = logging.getLogger(__name__)


   def create_app() -> Litestar:
       configure_logging(level=logging.INFO, json_format=True, include_trace=False)

       resource = Resource.create(
           attributes={
               "service.name": "litestar",
           },
       )
       tracer_provider = TracerProvider(resource=resource)
       trace.set_tracer_provider(tracer_provider)

       trace_config = TracingConfig(tracer_provider=tracer_provider)
       metrics_config = MetricsConfig(app_name="litestar", include_trace_exemplar=True)

       middlewares = [build_tracing_middleware(trace_config), build_metrics_middleware(metrics_config)]

       app = Litestar([index], middleware=middlewares, logging_config=None)
       add_metrics_endpoint(app, metrics_config.registry, openmetrics_format=False)

       return app


   if __name__ == "__main__":
       log_config = build_uvicorn_log_config(level=logging.INFO, json_format=True, include_trace=True)
       uvicorn.run(create_app(), host="127.0.0.1", port=8000, log_config=log_config)

If you want to use **StructlogPlugin** from ``litestar.plugins.structlog`` together with tracing, you can embed a processor in the structlog processor chain to export the trace context to the log.

.. code-block:: python
   :caption: Import processor for extract trace meta

   from asgi_monitor.logging.trace_processor import extract_opentelemetry_trace_meta
