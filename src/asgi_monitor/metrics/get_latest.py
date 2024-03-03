# https://habr.com/ru/companies/domclick/articles/773136/

import os
from dataclasses import dataclass

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    REGISTRY,
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
    status_code: int
    headers: dict[str, str]
    payload: bytes


def get_latest_metrics(*, openmetrics_format: bool) -> MetricsResponse:
    registry = REGISTRY

    if "PROMETHEUS_MULTIPROC_DIR" in os.environ:
        registry = CollectorRegistry()
        multiprocess.MultiProcessCollector(registry)

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
