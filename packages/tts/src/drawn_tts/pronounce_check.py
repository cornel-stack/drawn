"""Synthesise a channel's whole pronunciation map into one WAV for review.

``just pronounce-check <channel>`` speaks every mapped pronunciation in order,
so you can hear whether ``"Coulomb": "koo-lom"`` and friends actually come out
right and fix the spelling if not. The map is the safety net for the voice, and
this is how you listen to it.

Output: ``out/<channel>/pronounce-check.wav`` plus a printed index of what is
spoken at each timestamp.
"""

from __future__ import annotations

from pathlib import Path

from drawn_schema import paths, pronounce
from drawn_schema.channel import load_channel

from drawn_tts.service import SAMPLE_RATE, make_service


def run_pronounce_check(repo_root: Path, channel: str) -> Path:
    import tempfile

    import numpy as np
    import soundfile as sf

    mapping = pronounce.load_pronounce(Path(repo_root), channel)
    if not mapping:
        raise ValueError(f"no pronounce.yaml entries for {channel}")
    cfg = load_channel(repo_root, channel)
    service = make_service(cfg.voice)

    gap = np.zeros(int(SAMPLE_RATE * 0.45), dtype=np.float32)
    parts: list = []
    t = 0.0
    print(f"pronounce-check: {channel} ({len(mapping)} entries)")
    with tempfile.TemporaryDirectory() as tmp:
        for i, (key, spoken) in enumerate(mapping.items()):
            seg = Path(tmp) / f"p{i}.wav"
            service.synthesize(spoken, seg)
            a, _sr = sf.read(str(seg))
            a = np.asarray(a, dtype=np.float32)
            if a.ndim > 1:
                a = a.mean(axis=1)
            dur = len(a) / SAMPLE_RATE
            print(f"  [{t:6.1f}s] {key!r} -> {spoken!r}")
            parts.append(a)
            parts.append(gap)
            t += dur + len(gap) / SAMPLE_RATE

    audio = np.concatenate(parts) if parts else np.zeros(1, dtype=np.float32)
    out = paths.lesson_out_dir(repo_root, channel, "_pronounce") / "pronounce-check.wav"
    out.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(out), audio, SAMPLE_RATE)
    print(f"wrote {out} ({t:.1f}s)")
    return out


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="drawn-tts pronounce-check")
    parser.add_argument("channel")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    run_pronounce_check(args.repo_root, args.channel)
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
