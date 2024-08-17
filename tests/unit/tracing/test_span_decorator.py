import asyncio
import time

from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import TracerProvider

from asgi_monitor.tracing import span as span_decorator


def test_simple_span_decorator() -> None:
    # Arrange
    expected = 1

    @span_decorator
    def action() -> int:
        return expected

    # Act
    result = action()

    # Assert
    assert result == expected


def test_empty_span_decorator(exporter: InMemorySpanExporter, tracer_provider: TracerProvider) -> None:
    # Arrange
    @span_decorator(tracer=tracer_provider.get_tracer(__name__))
    def action() -> None:
        time.sleep(0.01)

    # Act
    action()

    # Assert
    span = exporter.get_finished_spans()[0]
    assert span.name == action.__name__
    assert span.attributes == {}


def test_span_decorator(exporter: InMemorySpanExporter, tracer_provider: TracerProvider) -> None:
    # Arrange
    @span_decorator(name="test", attributes={"test": "test"}, tracer=tracer_provider.get_tracer(__name__))
    def action() -> None:
        time.sleep(0.01)

    # Act
    action()

    # Assert
    span = exporter.get_finished_spans()[0]
    assert span.name == "test"
    assert span.attributes == {"test": "test"}


async def test_async_simple_span_decorator(exporter: InMemorySpanExporter, tracer_provider: TracerProvider) -> None:
    # Arrange
    expected = 1

    @span_decorator
    async def action() -> int:
        return expected

    # Act
    result = await action()

    # Assert
    assert result == expected


async def test_async_empty_span_decorator(exporter: InMemorySpanExporter, tracer_provider: TracerProvider) -> None:
    # Arrange
    @span_decorator(tracer=tracer_provider.get_tracer(__name__))
    async def action() -> None:
        await asyncio.sleep(0.01)

    # Act
    await action()

    # Assert
    span = exporter.get_finished_spans()[0]
    assert span.name == action.__name__
    assert span.attributes == {}


async def test_async_span_decorator(exporter: InMemorySpanExporter, tracer_provider: TracerProvider) -> None:
    # Arrange
    @span_decorator(name="test", attributes={"test": "test"}, tracer=tracer_provider.get_tracer(__name__))
    async def action() -> None:
        await asyncio.sleep(0.01)

    # Act
    await action()

    # Assert
    span = exporter.get_finished_spans()[0]
    assert span.name == "test"
    assert span.attributes == {"test": "test"}


async def test_nested_spans(exporter: InMemorySpanExporter, tracer_provider: TracerProvider) -> None:
    # Arrange
    tracer = tracer_provider.get_tracer(__name__)

    @span_decorator(tracer=tracer)
    async def count() -> int:
        return 1

    @span_decorator(tracer=tracer)
    async def action() -> None:
        num = await count()
        assert num == 1

    # Act
    await action()

    # Assert
    count_sleep, span_action = exporter.get_finished_spans()
    assert span_action.name == action.__name__
    assert span_action.attributes == {}
    assert count_sleep.name == count.__name__
    assert count_sleep.attributes == {}
    assert count_sleep.parent.span_id == span_action.context.span_id  # type: ignore[union-attr]
