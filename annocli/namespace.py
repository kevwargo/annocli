__all__ = ("Arg", "Namespace")

import argparse
import sys
from copy import copy
from functools import cached_property
from types import GenericAlias, NoneType, UnionType
from typing import Any, Iterable, Iterator, get_type_hints


class Namespace(argparse.Namespace):
    __verbose_parse__ = False

    def __init__(self, argv=None):
        parser = argparse.ArgumentParser()

        cls = type(self)
        cls_dict = cls.__dict__
        cls_annotations = get_type_hints(cls)

        for name in _filter_names(cls_dict | cls_annotations):
            attr = _Attr(name, cls_dict, cls_annotations)

            if self.__verbose_parse__:
                args_repr = ", ".join(map(repr, attr.args))
                kwargs_repr = ", ".join(f"{k}={v!r}" for k, v in attr.kwargs.items())
                print(f"parser.add_argument({args_repr}, {kwargs_repr})", file=sys.stderr)

            parser.add_argument(*attr.args, **attr.kwargs)

        parser.parse_args(argv, namespace=self)

    def __getattribute__(self, name):
        v = super().__getattribute__(name)
        if name.startswith("_"):
            return v

        if name not in self.__dict__:
            if isinstance(v, Arg):
                try:
                    v = v.kwargs["default"]
                except KeyError:
                    raise AttributeError(f"Attribute {name!r} is not set") from None

            vcopy = copy(v)
            if self.__verbose_parse__:
                print(f"setting default {name} = {v!r}({hex(id(v))} -> {hex(id(vcopy))})", file=sys.stderr)

            setattr(self, name, vcopy)

        return v


class Arg:
    def __init__(self, *args, positional=False, **kwargs):
        self.args = list(args)
        self.kwargs = kwargs
        self.positional = positional


class _Attr:
    def __init__(self, name: str, cls_dict: dict, cls_annotations: dict):
        self.name = name
        self.cls_dict = cls_dict
        self.cls_annotations = cls_annotations

    @cached_property
    def has_anno(self) -> bool:
        return self.name in self.cls_annotations

    @cached_property
    def anno(self) -> Any:
        return self.cls_annotations[self.name]

    @cached_property
    def custom(self) -> Arg | None:
        if (arg := self.cls_dict.get(self.name)) and isinstance(arg, Arg):
            return arg

        return None

    @cached_property
    def has_default(self) -> bool:
        if self.optional_type:
            return True

        if self.custom:
            if "default" in self.custom.kwargs:
                return True
        else:
            return self.name in self.cls_dict

    @cached_property
    def default(self) -> Any:
        if self.custom:
            if "default" in self.custom.kwargs:
                return self.custom.kwargs["default"]
        elif self.name in self.cls_dict:
            return self.cls_dict[self.name]

        if self.list_type:
            return []

        if self.is_bool:
            return False

    @cached_property
    def args(self) -> list[str]:
        if self.custom:
            if self.custom.positional:
                return self.custom.args or [self.name]

            if self.shorts_only:
                return [*self.custom.args, self.dash_arg]
            elif self.custom.args:
                return self.custom.args

        return [self.dash_arg]

    @cached_property
    def dash_arg(self) -> str:
        name = self.name.rstrip("_").replace("_", "-")
        return f"--{name}"

    @cached_property
    def shorts_only(self) -> bool:
        if not (self.custom and self.custom.args):
            return False

        return all(len(a) == 2 and a[0] == "-" and a[1].isalnum() for a in self.custom.args)

    @cached_property
    def kwargs(self):
        return {
            **({"type": self.resolved_type} if self.resolved_type and not self.is_bool else {}),
            **({"action": self.action} if self.action else {}),
            **({"required": True} if self.required and not self.positional else {}),
            **({"default": self.default} if self.has_default else {}),
            **({"nargs": self.nargs} if self.nargs else {}),
        }

    @cached_property
    def resolved_type(self) -> type[Any] | None:
        if self.custom and (typ := self.custom.kwargs.get("type")):
            return typ

        if not self.has_anno:
            return None

        if self.list_type:
            return self.list_type

        if self.optional_type:
            return self.optional_type

        return self.anno

    @cached_property
    def is_bool(self) -> bool:
        return self.resolved_type is bool and not self.list_type

    @cached_property
    def optional_type(self) -> type[Any] | None:
        if not self.has_anno:
            return None

        if isinstance(self.anno, UnionType) and len((args := self.anno.__args__)) == 2 and args[1] is NoneType:
            return args[0]

        return None

    @cached_property
    def action(self) -> str | None:
        if self.custom and (act := self.custom.kwargs.get("action")):
            return act

        if self.is_bool:
            return "store_true"

    @cached_property
    def required(self) -> bool:
        if self.custom and (req := self.custom.kwargs.get("required")):
            return req

        if self.optional_type or self.is_bool:
            return False

        return not self.has_default

    @cached_property
    def list_type(self) -> type[Any] | None:
        if not self.has_anno:
            return None

        anno = self.optional_type or self.anno

        if not (isinstance(anno, GenericAlias) and issubclass(anno.__origin__, list)):
            return None

        if len(anno.__args__) != 1:
            raise TypeError(f"Invalid list generic: {anno}")

        return anno.__args__[0]

    @cached_property
    def positional(self) -> bool:
        return self.custom and self.custom.positional

    @cached_property
    def nargs(self) -> str | None:
        if self.custom and "nargs" in self.custom.kwargs:
            return self.custom.kwargs["nargs"]

        if self.action == "append":
            return None

        if self.list_type:
            return "+" if self.required else "*"

        if self.positional and not self.required:
            return "?"


def _filter_names(names: Iterable[str]) -> Iterator[str]:
    return (n for n in names if not n.startswith("_"))
