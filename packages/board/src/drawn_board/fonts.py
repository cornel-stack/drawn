"""Register the vendored handwriting font with Pango for Manim ``Text``.

Formulas never use this font (they are MathTex / standard LaTeX); only prose,
titles and labels do.
"""

from __future__ import annotations

from pathlib import Path

_registered: set[str] = set()


def register_handwriting_font(repo_root: Path, font_file: str) -> None:
    """Register ``font_file`` (relative to repo root) once per process."""
    path = (Path(repo_root) / font_file).resolve()
    key = str(path)
    if key in _registered:
        return
    if not path.is_file():
        raise FileNotFoundError(f"handwriting font not found: {path}")
    import manimpango

    manimpango.register_font(str(path))
    _registered.add(key)
