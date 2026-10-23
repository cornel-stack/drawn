"""ffmpeg finishing stage: music bed, loudnorm, mux, meta.md, captions.srt."""

from drawn_finish.finish import FinishResult, run_finish
from drawn_finish.manifest import build_props, write_props

__all__ = ["FinishResult", "run_finish", "build_props", "write_props"]
