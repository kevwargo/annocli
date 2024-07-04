__all__ = ("entrypoint", "Arg", "Namespace")

import typing
from argparse import ArgumentParser
from functools import wraps
from inspect import FullArgSpec, getfullargspec
from types import NoneType, UnionType

from annocli.namespace import Arg, Namespace


def entrypoint(fn: typing.Callable) -> typing.Callable:
    spec = getfullargspec(fn)

    if ns := _parse_single_ns_arg(spec):
        args, kwargs = (ns,), {}
    else:
        args, kwargs = _parse_func_args(spec)

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


def _parse_func_args(spec: FullArgSpec) -> tuple[list, dict]:
    defaults = dict(spec.kwonlydefaults or {}) | dict(zip(reversed(spec.args), reversed(spec.defaults)))

    parser = _build_parser(defaults, spec.annotations, spec.args + spec.kwonlyargs)

    ns = parser.parse_args()
    args = [getattr(ns, a) for a in spec.args]
    kwargs = {a: getattr(ns, a) for a in spec.kwonlyargs}

    return args, kwargs


def _build_parser(defaults, annotations, all_names=None) -> ArgumentParser:
    parser = ArgumentParser()

    for name in all_names or (set(defaults) | set(annotations)):
        if name.startswith("_"):
            continue

        kwargs = {}

        if arg_type := annotations.get(name):
            if typing.get_origin(arg_type) is typing.Annotated:
                type_args = typing.get_args(arg_type)
                arg_type, annotated_metadata = type_args[0], type_args[1:]
            else:
                annotated_metadata = ()

            if arg_type == bool:
                kwargs["action"] = "store_true"
                kwargs["required"] = False
            elif opt := _extract_opt_from_union(arg_type):
                kwargs["type"] = opt
                kwargs["required"] = False
            else:
                kwargs["type"] = arg_type

        if name in defaults:
            kwargs["default"] = defaults[name]
        elif "required" not in kwargs:
            kwargs["required"] = True

        args = annotated_metadata + ("--" + name.replace("_", "-"),)

        parser.add_argument(*args, **kwargs)

    return parser


def _extract_opt_from_union(annotation: type | UnionType) -> type | None:
    if not isinstance(annotation, UnionType):
        return None

    if len(annotation.__args__) == 2 and annotation.__args__[1] == NoneType:
        return annotation.__args__[0]

    return None
