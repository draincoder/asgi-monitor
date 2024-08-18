.. _Prometheus: https://prometheus.io
.. _Grafana: https://grafana.com
.. _prometheus-client: https://prometheus.github.io/client_python/
.. _Gunicorn: https://gunicorn.org

Metrics
==================

The metrics in **asgi-monitor** are based on Prometheus_ metrics and implemented through prometheus-client_.

Prometheus
~~~~~~~~~~~~~~~~~~

Metrics in Prometheus are essential for monitoring and alerting purposes. Here are a few key points about Prometheus metrics:

* **Data Collection:** Prometheus collects metrics from monitored targets by scraping HTTP endpoints at regular intervals. This data is then stored in a time-series database.

* **Metric Types:** Prometheus supports four types of metrics: **Counter**, **Gauge**, **Histogram** and **Summary**. Each type serves a different purpose and provides valuable insights into the system's behavior.

* **Alerting:** Prometheus uses collected metrics to evaluate predefined alerting rules and trigger alerts when certain conditions are met. This proactive monitoring helps in identifying issues before they impact the system.

* **Visualization:** Prometheus metrics can be visualized using tools like Grafana_, allowing users to create custom dashboards and gain a better understanding of the system's performance over time.

* **Scalability:** Prometheus is designed to scale horizontally, meaning it can handle a large number of metrics and targets without compromising performance. This scalability is crucial for monitoring complex systems with multiple components.

These metrics play a crucial role in maintaining system health, identifying performance bottlenecks, and ensuring the overall reliability of the infrastructure.

Basic metrics
~~~~~~~~~~~~~~~~~~

By default, the following metrics are used in :ref:`integrations`:

1. ``prefix_app_info`` - Application information (**Gauge** type)
2. ``prefix_requests_total`` - Total count of requests by method and path [**Counter**]
3. ``prefix_responses_total`` - Total count of responses by method, path and status codes [**Counter**]
4. ``prefix_request_duration_seconds`` - Histogram of request duration by path, in seconds [**Histogram**]
5. ``prefix_requests_in_progress`` - Gauge of requests by method and path currently being processed [**Gauge**]
6. ``prefix_requests_exceptions_total`` - Total count of exceptions raised by path and exception type [**Counter**]

Configuration
~~~~~~~~~~~~~~~~~~

The ``BaseMetricsConfig`` class is used to configure metrics, and it accepts the following arguments as input:

1. ``app_name`` (**str**) - The name of the application.

2. ``metrics_prefix`` (**str**) - The prefix to use for the metrics. Each integration module uses its own ``MetricsConfig``, where the default value of the **metrics_prefix** corresponds to the name of the integration.

3. ``registry`` (**prometheus_client.CollectorRegistry**) - A registry for metrics. Default is ``prometheus_client.CollectorRegistry(auto_describe=True)``.

4. ``include_trace_exemplar`` (**bool**) - Whether to include trace exemplars in the metrics. Default is ``False``. This is only necessary if **tracing** is configured and metrics are collected in the ``OpenMetrics`` format.

5. ``openmetrics_format`` (**bool**) - A flag indicating whether to generate metrics in ``OpenMetrics`` format. Default is ``False``.


You can also set up a **global** ``prometheus_client.REGISTRY`` in ``MetricsConfig`` to support your **global** metrics,
but it is better to use your own **non-global** registry or leave the **default** registry.

.. code-block:: python
   :caption: Setting up MetricsConfig

   from asgi_monitor.integrations.fastapi import MetricsConfig

   metrics_config = MetricsConfig(
       app_name="asgi-monitor",        # Your application name
       include_trace_exemplar=False,   # Tracing is not used
       include_metrics_endpoint=True,  # Adding an endpoint /metrics
   )
   # Using default metrics_prefix "fastapi"
   # Using default metrics export format (``openmetrics_format=True`` for use ``OpenMetrics`` format)
   # Using default registry

Exporting
~~~~~~~~~~~~~~~~~~

If you are using integration with the web framework, you can add metric exports via the config by setting ``include_metrics_endpoint`` to ``True`` or by explicitly calling ``add_metrics_endpoint``.

In case you need to **customize the endpoint**, add **protection** or just use **another method for delivering** metrics, then you should use the built-in ``get_latest_metrics`` function.

.. code-block:: python
   :caption: Exporting metrics

   from asgi_monitor.metrics import get_latest_metrics

   metrics = get_latest_metrics(registry=registry)

Gunicorn
~~~~~~~~~~~~~~~~~~

If you are using Gunicorn_, then you need to set the environment variable **"PROMETHEUS_MULTIPROC_DIR"** with the path to the directory where the consistent metrics will be stored.
This approach will **block** the **event loop** when recording metrics.
