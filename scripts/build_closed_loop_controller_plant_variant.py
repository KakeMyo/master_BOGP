#!/usr/bin/env python3
"""Render a variant of slide 06 with controller/plant group frames.

This script intentionally writes a new image file and does not overwrite the
main slide image deck.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

import build_revised_12min_slide_images as base


OUT_DIR = base.ROOT / "slides" / "revised_12min_slide_variants"
OUT_PATH = OUT_DIR / "06_closed_loop_controller_plant_framed.png"


def rgba(hex_color: str, alpha: int) -> tuple[int, int, int, int]:
    r, g, b = base._rgb(hex_color)
    return r, g, b, alpha


def framed_group(
    img: Image.Image,
    box: tuple[int, int, int, int],
    label: str,
    subtitle: str,
    accent: str,
    fill: str,
    label_box: tuple[int, int, int, int],
) -> None:
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    odraw.rounded_rectangle(box, radius=24, fill=rgba(fill, 64), outline=rgba(accent, 220), width=7)
    composed = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    img.paste(composed)

    draw = ImageDraw.Draw(img)
    base.rounded(draw, label_box, accent, None, radius=12)
    base.draw_text(draw, (label_box[0] + 18, label_box[1] + 8), label, 24, base.C["white"], "bold")
    base.draw_text(draw, (label_box[0] + 18, label_box[1] + 42), subtitle, 17, "#EAF6FF", "regular")


def build() -> Image.Image:
    img = base.slide_06()
    framed_group(
        img,
        (565, 400, 985, 825),
        "Controller / 制御器",
        "BO制御器 + BO更新",
        base.C["cyan"],
        base.C["cyan_light"],
        (590, 356, 910, 424),
    )
    framed_group(
        img,
        (1335, 400, 1680, 635),
        "Plant / プラント",
        "GP進化プロセス",
        base.C["green"],
        base.C["green_light"],
        (1360, 356, 1638, 424),
    )

    draw = ImageDraw.Draw(img)
    base.rounded(draw, (260, 990, 1625, 1040), base.C["gray"], None, radius=14)
    base.draw_box_text(
        draw,
        (285, 990, 1600, 1040),
        "枠の整理: BO側をコントローラ，GP世代進化をプラントとして扱う",
        22,
        base.C["navy"],
        "bold",
        "center",
        "center",
        pad=0,
    )
    return img


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    build().save(OUT_PATH, quality=95)
    print(OUT_PATH)


if __name__ == "__main__":
    main()
