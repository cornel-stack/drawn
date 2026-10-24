"""Hand asset pipeline.

``just hand`` runs :func:`ensure_hand`:
  * if ``assets/hand/raw/*.jpg`` photos exist, cut out the background with
    rembg, autocrop, save ``hand_write.png`` (and ``hand_rest.png`` if a second
    photo exists), and write ``anchors.json`` with a detected pen-tip anchor;
  * otherwise generate a temporary fallback hand so lessons still render.

The pen-tip anchor defaults to the opaque region's top-left extreme (where a
right hand holds a pen pointing up-left). Confirm or override with
``set_tip(pose, nx, ny)`` or the click helper.
"""

from __future__ import annotations

import json
from pathlib import Path

HAND_DIR = "assets/hand"
ANCHORS = "anchors.json"
HEIGHT_FRAC = 0.40


def _dir(repo_root: Path) -> Path:
    return Path(repo_root) / HAND_DIR


def anchors_path(repo_root: Path) -> Path:
    return _dir(repo_root) / ANCHORS


def _detect_tip(png_path: Path) -> tuple[float, float]:
    """Pen-tip anchor as (nx, ny) fractions.

    For a right hand writing, the nib is the left-most opaque extreme (the pen
    points down-left, hand to the right). Take the left-most opaque column and
    the median row within it. Override with ``set_tip`` if it misses.
    """
    import numpy as np
    from PIL import Image

    im = Image.open(png_path).convert("RGBA")
    a = np.asarray(im)[:, :, 3]
    ys, xs = np.where(a > 32)
    if len(xs) == 0:
        return (0.12, 0.08)
    h, w = a.shape
    xmin = xs.min()
    band = xs <= xmin + max(2, int(0.01 * w))  # left-most ~1% of width
    tip_x = float(xs[band].mean())
    tip_y = float(np.median(ys[band]))
    return (round(tip_x / w, 4), round(tip_y / h, 4))


def _autocrop(im):
    import numpy as np

    a = np.asarray(im)[:, :, 3]
    ys, xs = np.where(a > 8)
    if len(xs) == 0:
        return im
    pad = 8
    x0, x1 = max(xs.min() - pad, 0), min(xs.max() + pad, a.shape[1])
    y0, y1 = max(ys.min() - pad, 0), min(ys.max() + pad, a.shape[0])
    return im.crop((x0, y0, x1, y1))


def process_raw(repo_root: Path) -> Path:
    """Cut out backgrounds from raw photos and write pngs + anchors.json."""
    from PIL import Image
    from rembg import remove

    hd = _dir(repo_root)
    raws = sorted((hd / "raw").glob("*.jpg")) + sorted((hd / "raw").glob("*.jpeg"))
    if not raws:
        raise FileNotFoundError(f"no raw photos under {hd / 'raw'}")

    poses = {}
    names = ["write", "rest"]
    for name, raw in zip(names, raws, strict=False):
        cut = remove(Image.open(raw).convert("RGBA"))
        cut = _autocrop(cut)
        out = hd / f"hand_{name}.png"
        cut.save(out)
        poses[name] = {"image": f"{HAND_DIR}/hand_{name}.png", "tip": list(_detect_tip(out))}

    data = {**poses, "height_frac": HEIGHT_FRAC}
    anchors_path(repo_root).write_text(json.dumps(data, indent=2))
    return anchors_path(repo_root)


def generate_fallback(repo_root: Path) -> Path:
    """Draw a plain placeholder hand+pen (pen tip near the top-left)."""
    from PIL import Image, ImageDraw

    hd = _dir(repo_root)
    hd.mkdir(parents=True, exist_ok=True)
    w, h = 460, 560
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    tip = (44, 40)
    # pen barrel from the tip down to the hand
    d.polygon([tip, (tip[0] + 30, tip[1] - 6), (320, 330), (284, 356)], fill=(235, 238, 245, 240))
    d.polygon([tip, (tip[0] + 18, tip[1] + 2), (tip[0] + 4, tip[1] + 18)], fill=(30, 32, 40, 255))
    # hand blob gripping the lower-right
    d.ellipse([250, 300, 440, 520], fill=(228, 198, 170, 235))
    d.ellipse([270, 268, 380, 372], fill=(228, 198, 170, 235))
    for i in range(4):
        y0 = 320 + i * 40
        d.rounded_rectangle([322, y0, 442, y0 + 30], radius=15, fill=(214, 184, 156, 240))
    out = hd / "hand_write.png"
    img.save(out)
    data = {
        "write": {
            "image": f"{HAND_DIR}/hand_write.png",
            "tip": [round(tip[0] / w, 4), round(tip[1] / h, 4)],
        },
        "height_frac": HEIGHT_FRAC,
        "_fallback": True,
    }
    anchors_path(repo_root).write_text(json.dumps(data, indent=2))
    return anchors_path(repo_root)


def ensure_hand(repo_root: Path) -> Path:
    repo_root = Path(repo_root)
    ap = anchors_path(repo_root)
    if ap.is_file():
        return ap
    raw = _dir(repo_root) / "raw"
    if raw.is_dir() and (list(raw.glob("*.jpg")) or list(raw.glob("*.jpeg"))):
        return process_raw(repo_root)
    return generate_fallback(repo_root)


def set_tip(repo_root: Path, pose: str, nx: float, ny: float) -> None:
    ap = anchors_path(repo_root)
    data = json.loads(ap.read_text())
    data.setdefault(pose, {})["tip"] = [nx, ny]
    ap.write_text(json.dumps(data, indent=2))


def _cli() -> None:
    import argparse

    p = argparse.ArgumentParser(prog="drawn-hand")
    p.add_argument("repo_root", nargs="?", default=".")
    p.add_argument("--rebuild", action="store_true", help="reprocess raw photos / fallback")
    p.add_argument("--tip", nargs=3, metavar=("POSE", "NX", "NY"),
                   help="override a pen-tip anchor")
    args = p.parse_args()
    root = Path(args.repo_root)
    if args.tip:
        set_tip(root, args.tip[0], float(args.tip[1]), float(args.tip[2]))
        print(f"set {args.tip[0]} tip")
        return
    if args.rebuild and anchors_path(root).is_file():
        anchors_path(root).unlink()
    path = ensure_hand(root)
    print(f"hand ready: {path}")


if __name__ == "__main__":
    _cli()
