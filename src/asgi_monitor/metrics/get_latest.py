# https://habr.com/ru/companies/domclick/articles/773136/

import os
from dataclasses import dataclass

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    generate_latest,
    multiprocess,
)
from prometheus_client.openmetrics.exposition import CONTENT_TYPE_LATEST as OPENMETRICS_CONTENT_TYPE_LATEST
from prometheus_client.openmetrics.exposition import generate_latest as openmetrics_generate_latest

__all__ = (
    "MetricsResponse",
    "get_latest_metrics",
)


@dataclass(frozen=True, slots=True)
class MetricsResponse:
    """
    Represents a response containing metrics data.
    """

    status_code: int
    headers: dict[str, str]
    payload: bytes


def get_latest_metrics(registry: CollectorRegistry, *, openmetrics_format: bool) -> MetricsResponse:
    """
    Generates the latest metrics data in either Prometheus or OpenMetrics format.

    :param CollectorRegistry registry: A registry for collect metrics.
    :param bool openmetrics_format: A flag indicating whether to generate metrics in OpenMetrics format.
    :returns: MetricsResponse
    """

    if path := os.environ.get("PROMETHEUS_MULTIPROC_DIR"):
        registry = CollectorRegistry()
        multiprocess.MultiProcessCollector(registry, path=path)

    if openmetrics_format:
        headers = {"Content-Type": OPENMETRICS_CONTENT_TYPE_LATEST}
        return MetricsResponse(
            headers=headers,
            status_code=200,
            payload=openmetrics_generate_latest(registry),
        )

    headers = {"Content-Type": CONTENT_TYPE_LATEST}
    return MetricsResponse(
        headers=headers,
        status_code=200,
        payload=generate_latest(registry),
    )
