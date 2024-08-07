__all__ = ("Arg", "Namespace")

import argparse
from types import NoneType, UnionType
from typing import Any


class Arg:
    def __init__(self, *args, positional=False, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.positional = positional


class _AttributeRecorder(dict):
    def __init__(self):
        super().__init__()

        self._names = []
        self._defaults = {}
        self._annotations = {}
        self._custom = {}

        self._annotations_recorder = _AnnotationsRecorder(self)

    def __setitem__(self, k, v):
        if k.startswith("_"):
            if k == "__annotations__":
                v = self._annotations_recorder
            super().__setitem__(k, v)
        else:
            self.record(k)

            if type(v) is Arg:
                self._custom[k] = v
            else:
                self._defaults[k] = v

    def record(self, name):
        if name not in self._names:
            self._names.append(name)


class _AnnotationsRecorder(dict):
    def __init__(self, attr_recorder: _AttributeRecorder):
        super().__init__()
        self._attr_recorder = attr_recorder

    def __setitem__(self, k, v):
        super().__setitem__(k, v)

        if not k.startswith("_"):
            self._attr_recorder.record(k)

            if type(v) is Arg:
                self._attr_recorder._custom[k] = v
            else:
                self._attr_recorder._annotations[k] = v


class _NSMeta(type):
    def __init__(cls, name, bases, body):
        cls.__arg_names__ = body._names
        cls.__default_args__ = body._defaults
        cls.__annotated_args__ = body._annotations
        cls.__custom_args__ = body._custom

    @classmethod
    def __prepare__(*args, **kwargs):
        return _AttributeRecorder()


class Namespace(argparse.Namespace, metaclass=_NSMeta):
    __arg_names__: list[str]
    __default_args__: dict[str, Any]
    __annotated_args__: dict[str, type]
    __custom_args__: dict[str, Arg]

    def __init__(self):
        parser = argparse.ArgumentParser()

        for name in self.__arg_names__:
            args = ()
            kwargs = {}

            positional = False
            optional = True

            if default := self.__default_args__.get(name):
                kwargs["default"] = default
            elif custom := self.__custom_args__.get(name):
                args, kwargs = custom.args, custom.kwargs
                if custom.positional:
                    args = (name,)
                    positional = True
                else:
                    kwargs["dest"] = name

            if annotation := self.__annotated_args__.get(name):
                annotation, optional = self._parse_annotation(annotation)
                if not positional and annotation is bool:
                    kwargs["action"] = "store_true"
                else:
                    kwargs["type"] = annotation

            if positional:
                if optional and "nargs" not in kwargs:
                    kwargs["nargs"] = argparse.OPTIONAL
            else:
                if not optional and "default" not in kwargs:
                    kwargs["required"] = True

            if not args or self._alias_only(args):
                args += ("--" + name.replace("_", "-"),)

            parser.add_argument(*args, **kwargs)

        parser.parse_args(namespace=self)

    @staticmethod
    def _parse_annotation(annotation: type | UnionType) -> tuple[type, bool]:
        if not isinstance(annotation, UnionType):
            return annotation, annotation is bool

        if len(annotation.__args__) == 2 and annotation.__args__[1] is NoneType:
            return annotation.__args__[0], True

        return annotation, False

    @staticmethod
    def _alias_only(args: tuple) -> bool:
        if not args or len(args) != 1:
            return False

        a = args[0]
        return len(a) == 2 and a[0] == "-" and a[1] != "-"
