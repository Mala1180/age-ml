import time
from typing import Callable, ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")


def timed_call(
    fn: Callable[P, R], *args: P.args, **kwargs: P.kwargs
) -> tuple[R, float]:
    start = time.perf_counter()
    result = fn(*args, **kwargs)
    duration = time.perf_counter() - start
    return result, duration
