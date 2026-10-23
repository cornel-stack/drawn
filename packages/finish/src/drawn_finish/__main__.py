"""CLI for the finishing package.

``python -m drawn_finish props  <lesson.yaml> [--quality preview|final]``
``python -m drawn_finish finish <lesson.yaml>``
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from drawn_finish.finish import run_finish
from drawn_finish.manifest import write_props


def _cmd_props(args: argparse.Namespace) -> int:
    path = write_props(args.repo_root, args.lesson, args.quality)
    print(f"props: {path}")
    return 0


def _cmd_finish(args: argparse.Namespace) -> int:
    run_finish(args.repo_root, args.lesson)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="drawn-finish")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("props", help="write Remotion input props.json")
    p.add_argument("lesson", type=Path)
    p.add_argument("--repo-root", type=Path, default=Path.cwd())
    p.add_argument("--quality", default="preview", choices=["preview", "final"])
    p.set_defaults(func=_cmd_props)

    f = sub.add_parser("finish", help="music bed, loudnorm, mux, meta, srt")
    f.add_argument("lesson", type=Path)
    f.add_argument("--repo-root", type=Path, default=Path.cwd())
    f.set_defaults(func=_cmd_finish)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
