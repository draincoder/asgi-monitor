# https://habr.com/ru/companies/domclick/articles/773136/

import os
from dataclasses import dataclass

from prometheus_client import (
    CollectorRegistry,
    multiprocess,
)
from prometheus_client.exposition import choose_encoder
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


def get_latest_metrics(
    registry: CollectorRegistry,
    *,
    openmetrics_format: bool,
    accept_header: str = "",
) -> MetricsResponse:
    """
    Generates the latest metrics data in either Prometheus or OpenMetrics format.

    :param CollectorRegistry registry: A registry for collect metrics.
    :param bool openmetrics_format: Whether to force OpenMetrics instead of negotiating the format.
    :param str accept_header: The request's Accept header used to negotiate the response format.
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

    encoder, content_type = choose_encoder(accept_header)
    return MetricsResponse(
        headers={"Content-Type": content_type},
        status_code=200,
        payload=encoder(registry),
    )
