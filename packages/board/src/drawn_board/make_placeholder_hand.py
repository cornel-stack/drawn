"""Generate a placeholder transparent hand+pen PNG and its hand.yaml.

Run once to vendor ``assets/hand/placeholder-hand.png``. The pen tip sits near
the top-left; ``hand.yaml`` records it as normalised coordinates so the
hand-follow code is independent of the actual image. Replace the PNG with a real
hand photo and update ``tip``/``scale`` to swap it in.
"""

from __future__ import annotations

from pathlib import Path


def generate(out_png: Path, out_yaml: Path) -> None:
    from PIL import Image, ImageDraw

    w, h = 420, 520
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    tip = (34, 32)  # pen tip, near top-left

    # pen barrel: a tapered quad from the tip down to the hand
    barrel = [tip, (tip[0] + 26, tip[1] - 6), (300, 300), (268, 326)]
    d.polygon(barrel, fill=(40, 44, 52, 235))
    # nib highlight at the very tip
    d.polygon([tip, (tip[0] + 16, tip[1] + 2), (tip[0] + 4, tip[1] + 16)], fill=(20, 22, 28, 255))

    # hand: a rounded blob gripping the lower part of the pen
    d.ellipse([230, 280, 410, 470], fill=(224, 196, 168, 230))
    d.ellipse([250, 250, 360, 340], fill=(224, 196, 168, 230))  # thumb bulge
    # a few finger ridges
    for i in range(4):
        y0 = 300 + i * 34
        d.rounded_rectangle([300, y0, 408, y0 + 26], radius=13, fill=(210, 180, 150, 235))

    out_png.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_png)

    rel_png = out_png.as_posix()
    # make the image path repo-relative if it sits under the cwd
    out_yaml.write_text(
        f"image: {rel_png}\n"
        f"tip: [{tip[0] / w:.4f}, {tip[1] / h:.4f}]\n"
        f"scale: 1.7\n"
    )


if __name__ == "__main__":
    import sys

    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    png = root / "assets" / "hand" / "placeholder-hand.png"
    yaml_path = root / "assets" / "hand" / "hand.yaml"
    generate(png, yaml_path)
    # rewrite image path as repo-relative
    text = yaml_path.read_text().replace(str(png), "assets/hand/placeholder-hand.png")
    yaml_path.write_text(text)
    print(f"wrote {png} and {yaml_path}")
