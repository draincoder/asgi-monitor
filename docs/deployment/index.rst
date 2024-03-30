.. _real_world: https://github.com/draincoder/asgi-monitor/tree/master/examples/real_world

Deployment
********************

In real_world_ example, you can see the configuration settings for the monitoring infrastructure:

* **Grafana** for visualization
* **Tempo** for storing traces
* **Loki** for storing logs
* **Prometheus** for storing and exporting metrics
* **Vector** for collecting logs from containers
* **Docker** for containerization and quick launch

.. warning::

   Use these configs as a basis, but you need to take care of setting up authorization and long-term storage of information!
