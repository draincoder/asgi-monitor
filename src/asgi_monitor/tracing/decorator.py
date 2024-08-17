import asyncio
from functools import wraps
from typing import Callable, Mapping, ParamSpec, Sequence, TypeVar, cast, overload

from opentelemetry import trace
from opentelemetry.trace import Tracer

__all__ = ("span",)


F_Spec = ParamSpec("F_Spec")
F_Return = TypeVar("F_Return")
Func = Callable[F_Spec, F_Return]
Attributes = Mapping[str, str | bool | int | float | Sequence[str] | Sequence[bool] | Sequence[int] | Sequence[float]]


def _span_wrapper(
    name: str | None,
    attributes: Attributes | None,
    tracer: Tracer | None,
) -> Callable[[Func], Func]:
    def span_decorator(func: Func) -> Func:
        name_ = name or func.__name__
        tracer_ = tracer or trace.get_tracer(__name__)

        @wraps(func)
        def sync_span_wrapper(*args: F_Spec.args, **kwargs: F_Spec.kwargs) -> F_Return:  # type: ignore[type-var]
            with tracer_.start_as_current_span(name=name_, attributes=attributes):
                result = func(*args, **kwargs)
            return cast(F_Return, result)

        @wraps(func)
        async def async_span_wrapper(*args: F_Spec.args, **kwargs: F_Spec.kwargs) -> F_Return:
            with tracer_.start_as_current_span(name=name_, attributes=attributes):
                result = await func(*args, **kwargs)
            return cast(F_Return, result)

        if asyncio.iscoroutinefunction(func):
            return async_span_wrapper
        return sync_span_wrapper

    return span_decorator


@overload
def span(
    call: Func,
    *,
    name: None = None,
    attributes: None = None,
    tracer: None = None,
) -> Func: ...


@overload
def span(
    call: None = None,
    *,
    name: str | None = None,
    attributes: Attributes | None = None,
    tracer: Tracer | None = None,
) -> Callable[[Func], Func]: ...


def span(
    call: Func | None = None,
    *,
    name: str | None = None,
    attributes: Attributes | None = None,
    tracer: Tracer | None = None,
) -> Callable[[Func], Func] | Func:
    wrap_decorator = _span_wrapper(name, attributes, tracer)
    if call is None:
        return wrap_decorator
    else:
        return wrap_decorator(call)
