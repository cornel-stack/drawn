"""Augmented matrix with animated elementary row operations (Gauss's method).

Displays an augmented coefficient matrix — a grid of entries with a vertical bar
separating the coefficients from the right-hand constants — and animates the
three elementary row operations on it:

* ``swap(i, j)`` — interchange two rows;
* ``scale(i, k)`` — multiply a row by a non-zero constant;
* ``combine(target, src, k)`` — add ``k`` times row ``src`` to row ``target``
  (the elimination step that clears an entry below a pivot).

``highlight(i, col)`` briefly emphasises a pivot entry. Reused across the linear
algebra elimination series (Gauss's method, echelon form, rank).
"""

from __future__ import annotations

import numpy as np

from drawn_board import style
from drawn_board.primitives.base import Primitive, register, step

_COL_DX = 1.05      # horizontal spacing between columns
_ROW_DY = 0.82      # vertical spacing between rows
_ENTRY_FS = 40


@register("matrix")
class Matrix(Primitive):
    """params:
      center: [x, y]    # frame centre of the matrix (default ANIM_CENTER)
      col_dx, row_dy    # optional spacing overrides

    steps: draw, highlight, swap, scale, combine.
    """

    is_3d = False

    def build(self) -> None:
        p = self.params
        c = p.get("center", style.ANIM_CENTER)
        self._center = np.array([c[0], c[1], 0.0])
        self._col_dx = float(p.get("col_dx", _COL_DX))
        self._row_dy = float(p.get("row_dy", _ROW_DY))
        self.M: list[list[float]] = []      # numeric entries
        self.cells: list[list] = []         # MathTex mobjects, row-major

    # -- helpers -----------------------------------------------------------

    @staticmethod
    def _fmt(v: float) -> str:
        r = round(float(v))
        if abs(v - r) < 1e-9:
            return str(int(r))
        return f"{v:.2f}".rstrip("0").rstrip(".")

    def _pos(self, i: int, j: int):
        nrows = len(self.M)
        ncols = len(self.M[0]) if self.M else 0
        x = (j - (ncols - 1) / 2.0) * self._col_dx
        # the augmentation bar adds a little gap before the last column
        if j == ncols - 1:
            x += 0.22
        y = ((nrows - 1) / 2.0 - i) * self._row_dy
        return self._center + np.array([x, y, 0.0])

    def _mk(self, v: float, i: int, j: int):
        from manim import MathTex

        m = MathTex(self._fmt(v), color=self.color(None), font_size=_ENTRY_FS)
        m.move_to(self._pos(i, j))
        return m

    def _brackets(self):
        from manim import Line, VGroup

        nrows, ncols = len(self.M), len(self.M[0])
        top = self._pos(0, 0)[1] + 0.42
        bot = self._pos(nrows - 1, 0)[1] - 0.42
        xl = self._pos(0, 0)[0] - 0.5
        xr = self._pos(0, ncols - 1)[0] + 0.5
        cx = self._center[0]
        ser = 0.16
        col = self.color(None)

        def brack(x, inward):
            v = Line([x, top, 0], [x, bot, 0], color=col, stroke_width=3)
            t = Line([x, top, 0], [x + inward * ser, top, 0], color=col, stroke_width=3)
            b = Line([x, bot, 0], [x + inward * ser, bot, 0], color=col, stroke_width=3)
            return VGroup(v, t, b)

        parts = [brack(xl, +1), brack(xr, -1)]
        # vertical augmentation bar between the last two columns (only for augmented
        # systems; a plain matrix, e.g. for a determinant, omits it)
        if getattr(self, "_augmented", True) and ncols >= 2:
            bar_x = (self._pos(0, ncols - 2)[0] + self._pos(0, ncols - 1)[0]) / 2.0
            parts.append(Line([bar_x, top, 0], [bar_x, bot, 0], color=col, stroke_width=2))
        return VGroup(*parts)

    # -- steps -------------------------------------------------------------

    @step
    def draw(self, run_time: float, rows: list = None, augmented: bool = True, **_):
        """Draw the matrix from `rows`. With augmented=True (default) a vertical bar
        separates the last column (the augmented system of a linear-equations lesson);
        augmented=False draws a plain matrix, e.g. for a determinant."""
        from manim import Create, VGroup, Write

        self._augmented = bool(augmented)
        self.M = [[float(v) for v in r] for r in (rows or [])]
        self.cells = [[self._mk(self.M[i][j], i, j) for j in range(len(self.M[i]))]
                      for i in range(len(self.M))]
        frame = self._brackets()
        allcells = VGroup(*[c for row in self.cells for c in row])
        self.scene.play(Create(frame), run_time=run_time * 0.35)
        self.scene.play(Write(allcells), run_time=run_time * 0.65)

    @step
    def highlight(self, run_time: float, i: int = 0, col: int = 0,
                  color: str = "blue", **_):
        """Emphasise the pivot entry at (i, col)."""
        from manim import Circle, Indicate

        cell = self.cells[i][col]
        ring = Circle(radius=0.34, color=self.color(color), stroke_width=4).move_to(cell)
        self.scene.play(Indicate(cell, color=self.color(color), scale_factor=1.4),
                        _create(ring), run_time=run_time)

    @step
    def swap(self, run_time: float, i: int = 0, j: int = 1, **_):
        """Interchange rows i and j."""
        self.M[i], self.M[j] = self.M[j], self.M[i]
        self.cells[i], self.cells[j] = self.cells[j], self.cells[i]
        anims = []
        for row_idx in (i, j):
            for col, cell in enumerate(self.cells[row_idx]):
                anims.append(cell.animate.move_to(self._pos(row_idx, col)))
        self.scene.play(*anims, run_time=run_time)

    @step
    def scale(self, run_time: float, i: int = 0, k: float = 1.0, color: str = "orange", **_):
        """Multiply row i by k."""
        from manim import Transform

        anims = []
        for j in range(len(self.M[i])):
            self.M[i][j] *= k
            new = self._mk(self.M[i][j], i, j).set_color(self.color(color))
            anims.append(Transform(self.cells[i][j], new))
        self.scene.play(*anims, run_time=run_time)
        for j in range(len(self.M[i])):
            self.cells[i][j].set_color(self.color(None))

    @step
    def combine(self, run_time: float, target: int = 1, src: int = 0, k: float = 1.0,
                color: str = "orange", zero: str = "green", **_):
        """Row `target` becomes row `target` + k * row `src` (elimination step)."""
        from manim import Transform

        old = list(self.M[target])
        for j in range(len(self.M[target])):
            self.M[target][j] = old[j] + k * self.M[src][j]
        anims = []
        for j in range(len(self.M[target])):
            became_zero = abs(self.M[target][j]) < 1e-9 and abs(old[j]) > 1e-9
            c = zero if became_zero else color
            new = self._mk(self.M[target][j], target, j).set_color(self.color(c))
            anims.append(Transform(self.cells[target][j], new))
        self.scene.play(*anims, run_time=run_time)
        # settle non-zero entries back to base ink; keep new zeros briefly tinted
        for j in range(len(self.M[target])):
            if abs(self.M[target][j]) > 1e-9:
                self.cells[target][j].set_color(self.color(None))


def _create(m):
    from manim import Create

    return Create(m)
