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


def _cmd_sheet(args: argparse.Namespace) -> int:
    import yaml
    from drawn_schema import paths
    from drawn_schema.lesson import Lesson

    from drawn_finish.sheet import build_sheet

    lesson = Lesson.model_validate(yaml.safe_load(args.lesson.read_text()))
    out_dir = paths.lesson_out_dir(args.repo_root.resolve(), lesson.channel, lesson.id)
    video = out_dir / "video.mp4"
    if not video.is_file():
        print(f"error: {video} not found; build the lesson first")
        return 1
    sheet = build_sheet(video, out_dir / "sheet.png")
    print(f"sheet: {sheet}")
    return 0


def _cmd_assemble(args: argparse.Namespace) -> int:
    from drawn_finish.assemble_ffmpeg import assemble

    out = assemble(args.repo_root, args.lesson, args.quality)
    print(f"assembly: {out}")
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

    a = sub.add_parser("assemble", help="ffmpeg: concat clips + caption bar + voice")
    a.add_argument("lesson", type=Path)
    a.add_argument("--repo-root", type=Path, default=Path.cwd())
    a.add_argument("--quality", default="final", choices=["preview", "final"])
    a.set_defaults(func=_cmd_assemble)

    f = sub.add_parser("finish", help="music bed, loudnorm, mux, meta, srt")
    f.add_argument("lesson", type=Path)
    f.add_argument("--repo-root", type=Path, default=Path.cwd())
    f.set_defaults(func=_cmd_finish)

    s = sub.add_parser("sheet", help="write a contact sheet (1 frame / 5s, 4 cols)")
    s.add_argument("lesson", type=Path)
    s.add_argument("--repo-root", type=Path, default=Path.cwd())
    s.set_defaults(func=_cmd_sheet)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
