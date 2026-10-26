"""Evaluate a worked problem's ``check:`` expression.

A ``check`` recomputes the problem's boxed answer in plain Python (numpy / math
/ sympy, no builtins) so the linter and the fact-check gate can both confirm the
number on the board is the number the maths gives.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CheckResult:
    got: float
    ok: bool
    message: str


def _namespace() -> dict:
    import math

    import numpy as np

    ns = {
        "__builtins__": {},
        "np": np,
        "numpy": np,
        "math": math,
        "pi": math.pi,
        "sqrt": math.sqrt,
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "abs": abs,
        "min": min,
        "max": max,
        "pow": pow,
    }
    try:
        import sympy

        ns["sympy"] = sympy
    except ImportError:
        pass
    return ns


def eval_check(expr: str, value: float, tol: float) -> CheckResult:
    """Recompute ``expr`` and compare to ``value`` within relative ``tol``."""
    try:
        got = float(eval(expr, _namespace()))  # noqa: S307 (authored, no builtins)
    except Exception as exc:  # noqa: BLE001
        return CheckResult(float("nan"), False, f"check expr failed to evaluate ({exc})")
    denom = abs(value) if value else 1.0
    if abs(got - value) / denom > tol:
        return CheckResult(
            got, False, f"check recomputed {got:.4g} but answer is {value:.4g} (tol {tol:.0%})"
        )
    return CheckResult(got, True, f"recomputed {got:.4g} ≈ {value:.4g} (tol {tol:.0%})")
