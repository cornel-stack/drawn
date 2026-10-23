"""CLI: ``python -m drawn_tts <lesson.yaml> [--repo-root .] [--force]``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from drawn_tts.stage import run_tts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="drawn-tts")
    parser.add_argument("lesson", type=Path)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--force", action="store_true", help="ignore the cache")
    parser.add_argument("--model", default="base", help="faster-whisper model size")
    args = parser.parse_args(argv)

    print(f"tts: {args.lesson}")
    results = run_tts(
        args.repo_root, args.lesson, force=args.force, model_size=args.model
    )
    total = sum(r.duration for r in results)
    print(f"done: {len(results)} scenes, {total:.1f}s audio")
    return 0


if __name__ == "__main__":
    sys.exit(main())
