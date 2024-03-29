.. _OpenTelemetry: https://opentelemetry.io
.. _opentelemetry-sdk: https://opentelemetry.io/docs/languages/python/
.. _opentelemetry-asgi: https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/asgi/asgi.html
.. _opentelemetry-exporter-jaeger: https://pypi.org/project/opentelemetry-exporter-jaeger/
.. _opentelemetry-exporter-otlp: https://pypi.org/project/opentelemetry-exporter-otlp/
.. _cookbook: https://opentelemetry.io/docs/languages/python/cookbook/
.. _Grafana: https://grafana.com

Tracing
==================

Tracing in **asgi-monitor** is based on OpenTelemetry_ and implemented via the opentelemetry-sdk_.

OpenTelemetry
~~~~~~~~~~~~~~~~~~

Here are some key benefits of using OpenTelemetry:

* **Traceability:** OpenTelemetry provides a way to trace requests as they flow through different services, allowing developers to gain insights into the flow of data and identify bottlenecks or issues in the system.

* **Performance Monitoring:** By tracing requests through the system, developers can monitor the performance of each service and identify areas for optimization or improvement.

* **Troubleshooting:** When issues arise in a distributed system, tracing through OpenTelemetry can help pinpoint the root cause of the problem by showing the path of a request and where it may have failed.

* **Observability:** OpenTelemetry enables developers to gain a better understanding of their system's behavior and performance by providing detailed information about requests, including timing, dependencies, and errors.

Configuration
~~~~~~~~~~~~~~~~~~

``BaseTracingConfig`` is a configuration class for the OpenTelemetry middleware, and it accepts the following arguments as input:

1. ``exclude_urls_env_key`` (**str**) - Key to use when checking whether a list of excluded urls is passed via ENV. Each integration module uses its own ``TracingConfig``, where the default value of the **metrics_prefix** corresponds to the name of the integration.

2. ``scope_span_details_extractor`` (**Callable[[Any], tuple[str, dict[str, Any]]]**) - Callback which should return a string and a tuple, representing the desired default span name and a dictionary with any additional span attributes to set. Each integration module uses its own ``TracingConfig``, where the default value of the **metrics_prefix** corresponds to the name of the integration.

3. ``server_request_hook_handler`` (**Callable[[Span, dict], None] | None**) - Optional callback which is called with the server span and ASGI scope object for every incoming request.

4. ``client_request_hook_handler`` (**Callable[[Span, dict], None] | None**) - Optional callback which is called with the internal span and an ASGI scope which is sent as a dictionary for when the method receive is called.

5. ``client_response_hook_handler`` (**Callable[[Span, dict], None] | None**) - Optional callback which is called with the internal span and an ASGI event which is sent as a dictionary for when the method send is called.

6. ``meter_provider`` (**MeterProvider | None**) - Optional meter provider to use.

7. ``tracer_provider`` (**TracerProvider | None**) - Optional tracer provider to use.

8. ``meter`` (**Meter | None**) - Optional meter to use.

Consult the opentelemetry-asgi_ documentation for more info about the configuration options.

If you are **not an expert** in OpenTelemetry, then you just need to pass only the configured ``tracer_provider`` and the traces will work:

.. code-block:: python
   :caption: Setting up TracingConfig

   from opentelemetry import trace
   from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
   from opentelemetry.sdk.resources import Resource
   from opentelemetry.sdk.trace import TracerProvider
   from opentelemetry.sdk.trace.export import BatchSpanProcessor
   from asgi_monitor.integrations.fastapi import TracingConfig


   resource = Resource.create(
       attributes={
           "service.name": "asgi-monitor",  # To identify the application
       },
   )
   tracer = TracerProvider(resource=resource)
   trace.set_tracer_provider(tracer)
   tracer.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint="http://asgi-monitor.tempo:4317")))

   trace_config = TracingConfig(tracer_provider=tracer)

Trace management
~~~~~~~~~~~~~~~~~~

You can use traces to track the execution of some code and perform, for example, performance analysis.

See the cookbook_ for more information.

.. code-block:: python
   :caption: Trace management

   import asyncio
   from opentelemetry import trace

   tracer = trace.get_tracer(__name__)

   async def get_1000ms() -> dict:
       with tracer.start_as_current_span("sleep 0.1"):
           await asyncio.sleep(0.1)
           logger.error("sick")
       with tracer.start_as_current_span("sleep 0.2"):
           await asyncio.sleep(0.2)
           logger.error("still sick")
       with tracer.start_as_current_span("sleep 0.3"):
           await asyncio.sleep(0.3)
           logger.warning("normal")
       with tracer.start_as_current_span("sleep 0.4"):
           await asyncio.sleep(0.4)
           logger.info("full energy")
       return {"message": "ok", "status": "success"}


Exporting
~~~~~~~~~~~~~~~~~~

To export traces, you must select and configure an exporter yourself:

* opentelemetry-exporter-jaeger_ to export to **Jaeger**
* opentelemetry-exporter-otlp_ for export via **gRPC** or **HTTP**
* ``InMemorySpanExporter`` from ``opentelemetry.sdk.trace.export.in_memory_span_exporter`` for local tests

There are also other exporters.


Visualization
~~~~~~~~~~~~~~~~~~

After setting up, you can see visualization of traces in Grafana_

.. image:: ../images/traces.png
   :alt: dashboard
