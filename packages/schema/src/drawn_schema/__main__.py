"""CLI: ``python -m drawn_schema lint <lesson.yaml>``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from drawn_schema.linter import lint_lesson_file


def _cmd_import_backlogs(args: argparse.Namespace) -> int:
    from drawn_schema.backlog import import_all

    counts = import_all(args.repo_root)
    if not counts:
        print(f"no channels found under {args.repo_root / 'channels'}")
        return 1
    for name, n in counts.items():
        print(f"ok: channels/{name}/backlog.yaml ({n} rows)")
    return 0


def _cmd_lint(args: argparse.Namespace) -> int:
    exit_code = 0
    for path in args.lessons:
        result = lint_lesson_file(path)
        for w in result.warnings:
            print(f"warning: {path}: {w}")
        for e in result.errors:
            print(f"error: {path}: {e}")
        if result.ok:
            print(f"ok: {path}")
        else:
            exit_code = 1
    return exit_code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="drawn-schema")
    sub = parser.add_subparsers(dest="command", required=True)

    lint = sub.add_parser("lint", help="validate one or more lesson files")
    lint.add_argument("lessons", nargs="+", type=Path)
    lint.set_defaults(func=_cmd_lint)

    imp = sub.add_parser("import-backlogs", help="build channels/*/backlog.yaml from xlsx")
    imp.add_argument("--repo-root", type=Path, default=Path.cwd())
    imp.set_defaults(func=_cmd_import_backlogs)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
