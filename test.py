#!/usr/bin/python3

from pathlib import Path

from annocli import Arg, Namespace


class DDBQueryArgs(Namespace):
    __verbose_parse__ = True

    table_name: str = Arg("-t")
    limit: int | None
    expr: str = Arg(positional=True)
    sort_expr: str | None = Arg(positional=True)
    items: list[str] | None = Arg(action="append")
    output: Path | None = Arg("-o")


a = DDBQueryArgs()
print(a)
