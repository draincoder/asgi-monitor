.. _FastAPI: https://fastapi.tiangolo.com
.. _Starlette: https://www.starlette.io
.. _real_world: https://github.com/draincoder/asgi-monitor/tree/master/examples/real_world

.. _integrations:

Integrations
*******************************

Integration with the following frameworks is **now** implemented:

* FastAPI_
* Starlette_

But other integrations are planned in the near future, and you can also implement your own through **PR**.

FastAPI & Starlette
====================

These frameworks have the **same** integration api, so here I will show you how to configure monitoring for **FastAPI**.

.. code-block:: python
   :caption: Configuring monitoring for the FastAPI

   from asgi_monitor.integrations.fastapi import MetricsConfig, TracingConfig, setup_metrics, setup_tracing
   from asgi_monitor.logging import configure_logging
   from asgi_monitor.logging.uvicorn import build_uvicorn_log_config
   from fastapi import APIRouter, FastAPI
   from opentelemetry import trace
   from opentelemetry.sdk.resources import Resource
   from opentelemetry.sdk.trace import TracerProvider
   import uvicorn



   def run_app() -> None:
       configure_logging(level=logging.INFO, json_format=True, include_trace=False)

        resource = Resource.create(
            attributes={
                "service.name": "fastapi",
            },
        )
        tracer = TracerProvider(resource=resource)
        trace.set_tracer_provider(tracer)

        trace_config = TracingConfig(tracer_provider=tracer)
        metrics_config = MetricsConfig(app_name="fastapi", include_trace_exemplar=True)

        app = FastAPI(debug=True)
        app.include_router(router)

        setup_metrics(app=app, config=metrics_config)
        setup_tracing(app=app, config=trace_config)  # Must be configured last

        return app


   if __name__ == "__main__":
      log_config = build_uvicorn_log_config(level=logging.INFO, json_format=True, include_trace=True)
      uvicorn.run(create_app(), host="127.0.0.1", port=8000, log_config=log_config)


For **Starlette**, simply replace ``fastapi`` with ``starlette`` in the **integration** import line.

Check out the real_world_ example to figure out how it works.
