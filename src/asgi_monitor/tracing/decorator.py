from typing import Callable, Mapping, ParamSpec, Sequence, TypeVar, overload

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
) -> Callable[[Func[F_Spec, F_Return]], Func[F_Spec, F_Return]]:
    def span_decorator(func: Func[F_Spec, F_Return]) -> Func[F_Spec, F_Return]:
        name_ = name or func.__name__
        tracer_ = tracer or trace.get_tracer(__name__)

        return tracer_.start_as_current_span(name=name_, attributes=attributes)(func)

    return span_decorator


@overload
def span(
    call: Func[F_Spec, F_Return],
    *,
    name: None = None,
    attributes: None = None,
    tracer: None = None,
) -> Func[F_Spec, F_Return]: ...


@overload
def span(
    call: None = None,
    *,
    name: str | None = None,
    attributes: Attributes | None = None,
    tracer: Tracer | None = None,
) -> Callable[[Func[F_Spec, F_Return]], Func[F_Spec, F_Return]]: ...


def span(
    call: Func[F_Spec, F_Return] | None = None,
    *,
    name: str | None = None,
    attributes: Attributes | None = None,
    tracer: Tracer | None = None,
) -> Callable[[Func[F_Spec, F_Return]], Func[F_Spec, F_Return]] | Func[F_Spec, F_Return]:
    wrap_decorator = _span_wrapper(name, attributes, tracer)
    if call is None:
        return wrap_decorator
    else:
        return wrap_decorator(call)
