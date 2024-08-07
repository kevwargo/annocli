__all__ = ("entrypoint", "Arg", "Namespace")

import typing
from functools import wraps
from inspect import FullArgSpec, getfullargspec

from annocli.namespace import Arg, Namespace


def entrypoint(fn: typing.Callable) -> typing.Callable:
    spec = getfullargspec(fn)

    if ns := _parse_single_ns_arg(spec):
        args, kwargs = (ns,), {}
    else:
        raise NotImplementedError("Only single Namespace argument for entrypoints is supported currently")

    @wraps(fn)
    def wrapped():
        fn(*args, **kwargs)

    return wrapped


def _parse_single_ns_arg(spec: FullArgSpec) -> Namespace | None:
    if len(spec.args) != 1:
        return None

    if annotation := spec.annotations.get(spec.args[0]):
        if isinstance(annotation, type) and issubclass(annotation, Namespace):
            return annotation.__parse__()

    return None
