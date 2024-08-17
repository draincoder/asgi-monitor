.. _structlog: https://www.structlog.org
.. _Uvicorn: https://www.uvicorn.org
.. _Gunicorn: https://gunicorn.org
.. _examples: https://github.com/draincoder/asgi-monitor/tree/master/examples

Logging
==================

The logging in **asgi-monitor** are based on structlog_  with native logging module support.

Why **logging** is important for an application:

* **Troubleshooting:** Logging helps to identify and diagnose issues in the application by providing a detailed record of events and errors.

* **Monitoring:** Logging allows for real-time monitoring of the application's performance and behavior, helping to detect anomalies and potential problems.

* **Auditing:** Logging provides a trail of actions taken within the application, which can be useful for auditing and compliance purposes.

* **Performance Analysis:** Logs can be used to analyze the performance of the application, identify bottlenecks, and optimize its efficiency.

* **Security:** Logging helps in tracking security-related events, such as unauthorized access attempts or suspicious activities, to enhance the application's security posture.


Features
~~~~~~~~~~~~~~~~~~

Logging in the library provides the following features:

1. Logging in **JSON** format
2. Embedding **trace** attributes
3. **One-line** logging setup

Configuration
~~~~~~~~~~~~~~~~~~

``configure_logging`` accepts the following arguments as input:

1. ``level`` (**str | int**) - Logging level. Default is ``logging.INFO``.
2. ``json_format`` (**bool**) - The format of the logs. If ``True``, the log will be rendered as JSON.
3. ``include_trace`` (**bool**) - Include tracing information (``trace_id``, ``span_id``, ``parent_span_id``, ``service.name``).

An example of a JSON logging configuration with the declaration of a ``logging`` logger and a ``structlog`` logger. They adhere to the same format, but the interaction with them at the code level differs.

See structlog_ documentation for

.. code-block:: python
   :caption: Configure JSON logging

   import logging
   import structlog
   from asgi_monitor.logging import configure_logging

   logger = logging.getLogger(__name__)
   structlogger = structlog.getLogger(__name__)

   configure_logging(level=logging.INFO, json_format=True, include_trace=False)

   logger.info("Hello!")

   # {"event": "Hello!", "level": "info", "logger": "__main__", "timestamp": "2024-03-30 17:07:57.226293", "func_name": "<module>", "thread_name": "MainThread", "process_name": "MainProcess", "filename": "example.py", "process": 14751, "pathname": "/example.py", "thread": 8385919680, "module": "example"}

   logger.info("Bonjour!", extra={"language": "fr"})

    # {"event": "Bonjour!", "level": "info", "logger": "__main__", "language": "fr", "timestamp": "2024-03-30 17:07:57.226545", "func_name": "<module>", "thread_name": "MainThread", "process_name": "MainProcess", "filename": "example.py", "process": 14751, "pathname": "/example.py", "thread": 8385919680, "module": "example"}

   structlogger.info("Bonjour!", language="fr")

   # {"language": "fr", "event": "Bonjour!", "level": "info", "logger": "__main__", "timestamp": "2024-03-30 17:07:57.226588", "func_name": "<module>", "thread_name": "MainThread", "process_name": "n/a", "filename": "example.py", "process": 14751, "pathname": "/example.py", "thread": 8385919680, "module": "example"}

The time zone is set to ``UTC``, as this allows you to avoid time inconsistency when deploying on different servers in different time zones.

.. code-block:: python
   :caption: Configure console logging

   import logging
   import structlog
   from asgi_monitor.logging import configure_logging

   logger = logging.getLogger(__name__)
   structlogger = structlog.getLogger(__name__)

   configure_logging(level=logging.INFO, json_format=False, include_trace=False)

   logger.info("Hello!")

   # 2024-03-30 17:25:11.731512 [info] Hello!      [__main__] filename=example.py func_name=<module> module=example pathname=/example.py process=15622 process_name=MainProcess thread=8385919680 thread_name=MainThread

   logger.info("Bonjour!", extra={"language": "fr"})

   # 2024-03-30 17:25:11.731735 [info] Bonjour!    [__main__] filename=example.py func_name=<module> language=fr module=example pathname=/example.py process=15622 process_name=MainProcess thread=8385919680 thread_name=MainThread

   structlogger.info("Bonjour!", language="fr")

   # 2024-03-30 17:25:11.731781 [info] Bonjour!    [__main__] filename=example.py func_name=<module> language=fr module=example pathname=/example.py process=15622 process_name=n/a thread=8385919680 thread_name=MainThread

See the structlog_ documentation to familiarize yourself with all the features of this library.

But in your code, I recommend declaring loggers via ``logging`` to avoid binding to ``structlog``.

Tracing
~~~~~~~~~~~~~~~~~~

If ``include_trace=True``, then you will add the ``trace context`` to the log.

This makes it possible to map the trace to the log and switch between them in your visualization system.

.. code-block:: python
   :caption: Using with tracing

   configure_logging(level=logging.INFO, json_format=False, include_trace=True)

   tracer = trace.get_tracer(__name__)

   with tracer.start_as_current_span("parent span"):
       logger.info("start execution")

       # 2024-03-30 18:01:40.274833 [info] start execution    [__main__] filename=example.py func_name=<module> module=example pathname=/example.py process=16602 process_name=MainProcess service.name=fastapi span_id=6b15400b6764f747 thread=8385919680 thread_name=MainThread trace_id=d1dc4e05da452f29c56cf4f3c3963794
                                                                                                                                                                                          ^^^^^^^^^^^^^^^^^^^^ ^^^^^^^^^^^^^^^^^^^^^^^^                                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
       with tracer.start_as_current_span("child span"):
           logger.info("execution step one")

           # 2024-03-30 18:01:40.275193 [info] execution step one    [__main__] filename=example.py func_name=<module> module=example parent_span_id=6b15400b6764f747 pathname=/example.py process=16602 process_name=MainProcess service.name=fastapi span_id=a3586e6f36d675e1 thread=8385919680 thread_name=MainThread trace_id=d1dc4e05da452f29c56cf4f3c3963794
                                                                                                                                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^                                                             ^^^^^^^^^^^^^^^^^^^^ ^^^^^^^^^^^^^^^^^^^^^^^^                                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. tip::

   You can embed a processor in the **structlog** processor chain to export the trace context to the log.

.. code-block:: python
   :caption: Import processor for extract trace meta

   from asgi_monitor.logging.trace_processor import extract_opentelemetry_trace_meta

Uvicorn
~~~~~~~~~~~~~~~~~~

In order to apply the same logging logic for Uvicorn_, you must pass ``log_config`` as the ``server startup argument``.

.. code-block:: python
   :caption: Configure Uvicorn log_config

   import logging
   import uvicorn
   from asgi_monitor.logging.uvicorn import build_uvicorn_log_config

   log_config = build_uvicorn_log_config(level=logging.INFO, json_format=True, include_trace=True)
   uvicorn.run(app, host="127.0.0.1", port=8000, log_config=log_config)

Or the path to the config when starting uvicorn via the ``CLI``.

.. code-block:: text
   :caption: Configure Uvicorn log_config via CLI

   asgi-monitor uvicorn-log-config --path log-config.json --level info --json-format --include-trace

   uvicorn main:app --log-config log-config.json

In this case, you can save the config only in ``JSON`` format.

Call the command ``asgi-monitor uvicorn-log-config --help`` to find out the arguments.


Gunicorn
~~~~~~~~~~~~~~~~~~

If you need to run the application through Gunicorn_, then custom ``UvicornWorker``'s will help you with this.

That's what every UvicornWorker is responsible for:

1. ``StructlogTextLogUvicornWorker`` level: **DEBUG**, json_format: **False**, include_trace: **False**
2. ``StructlogTraceTextLogUvicornWorker`` level: **DEBUG**, json_format: **False**, include_trace: **True**
3. ``StructlogJSONLogUvicornWorker`` level: **DEBUG**, json_format: **True**, include_trace: **False**
4. ``StructlogTraceJSONLogUvicornWorker`` level: **DEBUG**, json_format: **True**, include_trace: **True**


.. code-block:: python
   :caption: Configure Gunicorn log_config

   import logging
   from asgi_monitor.logging.gunicorn import GunicornStandaloneApplication, StubbedGunicornLogger


   level = logging.DEBUG
   worker_class = "asgi_monitor.logging.uvicorn.worker.StructlogJSONLogUvicornWorker"  # Just select the right worker
   options = {
       "bind": "127.0.0.1",
       "workers": 1,
       "loglevel": logging.getLevelName(level),
       "worker_class": worker_class,
       "logger_class": StubbedGunicornLogger,
   }

   GunicornStandaloneApplication(app, options).run()


Check out the examples_ to figure out how it works.
