__all__ = ("entrypoint", "Arg", "Namespace")

import typing
from functools import wraps
from inspect import FullArgSpec, getfullargspec

from annocli.namespace import Arg, Namespace


def entrypoint(fn: typing.Callable) -> typing.Callable:
    spec = getfullargspec(fn)

    @wraps(fn)
    def wrapped():
        ns = _parse_single_ns_arg(spec)
        if not ns:
            raise NotImplementedError("Only single Namespace argument for entrypoints is supported currently")

        fn(ns())

    return wrapped


def _parse_single_ns_arg(spec: FullArgSpec) -> type[Namespace] | None:
    if len(spec.args) != 1:
        return None

    if annotation := spec.annotations.get(spec.args[0]):
        if isinstance(annotation, type) and issubclass(annotation, Namespace):
            return annotation

    return None
