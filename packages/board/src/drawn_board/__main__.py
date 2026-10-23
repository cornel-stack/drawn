"""CLI: render lesson scenes to silent clips.

``python -m drawn_board <lesson.yaml> [--scene s2] [--quality preview|final] [--force]``
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from drawn_board.render import render_all, render_scene


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="drawn-board")
    parser.add_argument("lesson", type=Path)
    parser.add_argument("--scene", help="render only this scene id")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--quality", default="preview", choices=["preview", "final"])
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)

    print(f"board: {args.lesson} ({args.quality})")
    if args.scene:
        render_scene(
            args.repo_root, args.lesson, args.scene, quality=args.quality, force=args.force
        )
    else:
        render_all(args.repo_root, args.lesson, quality=args.quality, force=args.force)
    return 0


if __name__ == "__main__":
    sys.exit(main())
