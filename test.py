#!/usr/bin/python3

from annocli import Arg, Namespace, entrypoint


class Arguments(Namespace):
    opt: int | None = Arg("-o")
    req: str = Arg(positional=True)
    bbb: bool


@entrypoint
def main(args: Arguments):
    print(f"opt={args.opt!r} req={args.req!r} bbb={args.bbb!r}")


if __name__ == "__main__":
    main()
