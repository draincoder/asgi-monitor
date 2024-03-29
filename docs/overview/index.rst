Overview
********************

Wor what?
==================

.. _Prometheus: https://prometheus.io
.. _OpenTelemetry: https://opentelemetry.io
.. _Structlog: https://www.structlog.org
.. _Grafana: https://grafana.com

The purpose of the library is to easily integrate the application with the **monitoring** infrastructure:

* Prometheus_ metrics
* OpenTelemetry_ traces
* Structlog_ logging with native **logging** module support

Benefits of monitoring
======================

* **Real-time Visibility:** Monitoring web applications provides real-time visibility into their performance, allowing for quick identification and resolution of issues.

* **Optimization:** By monitoring key metrics such as response time, error rates, and user experience, organizations can optimize their web applications for better performance.

* **Proactive Issue Detection:** Monitoring helps in the early detection of potential issues before they escalate, reducing downtime and ensuring a seamless user experience.

* **Capacity Planning:** Monitoring helps in understanding the resource utilization of web applications, enabling organizations to plan for future capacity requirements effectively.

* **Security:** Monitoring can also help in detecting security vulnerabilities and unauthorized access attempts, enhancing the overall security posture of web applications.



Installation
==================

.. code-block:: text

    pip install asgi-monitor

Example
==================

.. code-block:: python
   :caption: Adding metrics to the FastAPI

   from asgi_monitor.integrations.fastapi import setup_metrics, MetricsConfig
   from fastapi import FastAPI
   from uvicorn import run


   def run_app() -> None:
       app = FastAPI()
       setup_metrics(app, MetricsConfig(app_name="fastapi"))
       run(app, host="127.0.0.1", port=8000)


   if __name__ == "__main__":
       run_app()

After setting up, you can see visualization of default metrics in Grafana_

.. image:: ../images/metrics.png
   :alt: dashboard

Requirements
==================

* Python 3.10+
