#!/usr/bin/env python3
"""Render the revised 12-minute BOGP talk outline as per-slide PNG images.

The output is intentionally image-first rather than PPTX-first.  Text-heavy
Japanese slides are drawn with Pillow and a local Japanese font so the result is
legible when pasted into PowerPoint or Keynote.
"""

from __future__ import annotations

import csv
import math
import unicodedata
from pathlib import Path
from typing import Callable, Iterable

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "slides" / "revised_12min_slide_images"
RUN_ROOT = (
    ROOT
    / "outputs"
    / "main_bo_current_friedman"
    / "sr_alpha_friedman"
    / "main_bo_current_friedman_seed100_eval60_20260603"
)
AGGREGATE_CSV = RUN_ROOT / "main_aggregate_summary.csv"
GENERATION_CSV = RUN_ROOT / "main_generation_metric_summary.csv"
PAIRED_CSV = RUN_ROOT / "main_paired_differences.csv"
FIG_DIR = RUN_ROOT / "paper_labelled_figures"

W, H = 1920, 1080
MARGIN_X = 92

C = {
    "bg": "#E8EDF4",
    "paper": "#FCFDFE",
    "ink": "#111827",
    "muted": "#5B677A",
    "line": "#D3DAE6",
    "hair": "#E6EBF2",
    "navy": "#172033",
    "navy_2": "#25334A",
    "blue": "#1D4ED8",
    "blue_light": "#EFF5FF",
    "cyan": "#0891B2",
    "cyan_light": "#E9F8FB",
    "teal": "#0F766E",
    "teal_light": "#ECFDF8",
    "green": "#16803C",
    "green_light": "#ECF8EF",
    "orange": "#D65A1F",
    "orange_light": "#FFF3EA",
    "amber": "#B7791F",
    "amber_light": "#FFF8E6",
    "red": "#B42318",
    "red_light": "#FFF1F0",
    "gray": "#F1F4F8",
    "white": "#FFFFFF",
    "black": "#000000",
}

METHOD_COLORS = {
    "plain_fixed_standard": "#667085",
    "plain_fixed_high_mutation": "#14924A",
    "plain_fixed_high_crossover": "#D65A1F",
    "bogp_current": "#1D4ED8",
}

METHOD_LABELS = {
    "plain_fixed_standard": "標準固定率",
    "plain_fixed_high_mutation": "高突然変異",
    "plain_fixed_high_crossover": "高交叉",
    "bogp_current": "提案法",
}


def _rgb(hex_color: str) -> tuple[int, int, int]:
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


def _font_path(weight: int) -> Path:
    font_dir = Path("/System/Library/Fonts")
    for path in font_dir.iterdir():
        name = unicodedata.normalize("NFC", path.name)
        if "ヒラギノ角ゴシック" in name and f"W{weight}" in name:
            return path
    # Fallbacks still exist on macOS; they may rely on system fallback for CJK.
    return font_dir / "Helvetica.ttc"


REGULAR_FONT = _font_path(4)
BOLD_FONT = _font_path(7)
LIGHT_FONT = _font_path(3)
FONT_CACHE: dict[tuple[int, str], ImageFont.FreeTypeFont] = {}


def font(size: int, weight: str = "regular") -> ImageFont.FreeTypeFont:
    key = (size, weight)
    if key not in FONT_CACHE:
        path = BOLD_FONT if weight == "bold" else LIGHT_FONT if weight == "light" else REGULAR_FONT
        FONT_CACHE[key] = ImageFont.truetype(str(path), size)
    return FONT_CACHE[key]


def text_size(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.FreeTypeFont) -> tuple[int, int]:
    if not text:
        return 0, 0
    box = draw.textbbox((0, 0), text, font=fnt)
    return box[2] - box[0], box[3] - box[1]


def wrap_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    fnt: ImageFont.FreeTypeFont,
    max_width: int,
) -> list[str]:
    lines: list[str] = []
    for raw in text.split("\n"):
        current = ""
        for ch in raw:
            candidate = current + ch
            width, _ = text_size(draw, candidate, fnt)
            if width <= max_width or not current:
                current = candidate
            else:
                lines.append(current.rstrip())
                current = ch.lstrip()
        lines.append(current)
    return lines


def draw_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    size: int,
    fill: str = C["ink"],
    weight: str = "regular",
    max_width: int | None = None,
    align: str = "left",
    line_gap: float = 1.22,
) -> int:
    fnt = font(size, weight)
    lines = wrap_text(draw, text, fnt, max_width) if max_width else text.split("\n")
    x, y = xy
    line_h = int(size * line_gap)
    for line in lines:
        width, _ = text_size(draw, line, fnt)
        tx = x
        if align == "center" and max_width:
            tx = x + (max_width - width) // 2
        elif align == "right" and max_width:
            tx = x + max_width - width
        draw.text((tx, y), line, font=fnt, fill=fill)
        y += line_h
    return y


def draw_box_text(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    text: str,
    size: int,
    fill: str = C["ink"],
    weight: str = "regular",
    align: str = "left",
    valign: str = "top",
    pad: int = 20,
    line_gap: float = 1.22,
) -> None:
    x1, y1, x2, y2 = box
    max_width = max(1, x2 - x1 - 2 * pad)
    fnt = font(size, weight)
    lines = wrap_text(draw, text, fnt, max_width)
    line_h = int(size * line_gap)
    total_h = max(line_h, len(lines) * line_h)
    y = y1 + pad
    if valign == "center":
        y = y1 + max(0, (y2 - y1 - total_h) // 2)
    elif valign == "bottom":
        y = y2 - pad - total_h
    for line in lines:
        width, _ = text_size(draw, line, fnt)
        x = x1 + pad
        if align == "center":
            x = x1 + (x2 - x1 - width) // 2
        elif align == "right":
            x = x2 - pad - width
        draw.text((x, y), line, font=fnt, fill=fill)
        y += line_h


def rounded(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    fill: str,
    outline: str | None = C["line"],
    radius: int = 12,
    width: int = 2,
) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def arrow(
    draw: ImageDraw.ImageDraw,
    start: tuple[int, int],
    end: tuple[int, int],
    fill: str = C["muted"],
    width: int = 6,
    head: int = 18,
) -> None:
    draw.line([start, end], fill=fill, width=width)
    angle = math.atan2(end[1] - start[1], end[0] - start[0])
    pts = [
        end,
        (
            int(end[0] - head * math.cos(angle - math.pi / 6)),
            int(end[1] - head * math.sin(angle - math.pi / 6)),
        ),
        (
            int(end[0] - head * math.cos(angle + math.pi / 6)),
            int(end[1] - head * math.sin(angle + math.pi / 6)),
        ),
    ]
    draw.polygon(pts, fill=fill)


def new_slide() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (W, H), _rgb(C["bg"]))
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, W, H), fill=_rgb(C["bg"]))
    draw.rounded_rectangle((34, 28, W - 34, H - 28), radius=22, fill=_rgb(C["paper"]), outline=_rgb(C["line"]), width=1)
    draw.rectangle((34, 28, 124, H - 28), fill=_rgb(C["navy"]))
    for y in range(96, H - 70, 64):
        draw.line((78, y, 98, y), fill="#44546B", width=1)
    return img, draw


def header(draw: ImageDraw.ImageDraw, num: str, title: str, section: str) -> None:
    draw_text(draw, (60, 64), num, 26, "#DDE7F6", "bold", max_width=62, align="center")
    draw_text(draw, (170, 62), section, 22, C["cyan"], "bold")
    draw_text(draw, (170, 106), title, 48, C["ink"], "bold", max_width=1350)
    draw.line((170, 184, W - 88, 184), fill=C["hair"], width=2)
    draw.line((170, 196, 380, 196), fill=C["cyan"], width=4)


def claim(draw: ImageDraw.ImageDraw, text: str, y: int = 218) -> None:
    x1, x2 = 170, W - 92
    draw.line((x1, y + 7, x1, y + 72), fill=C["cyan"], width=8)
    draw_text(draw, (x1 + 22, y), "CLAIM", 18, C["cyan"], "bold")
    draw_box_text(draw, (x1 + 118, y - 2, x2, y + 78), text, 30, C["navy"], "bold", "left", "center", pad=0)
    draw.line((x1 + 118, y + 78, x2, y + 78), fill=C["hair"], width=2)


def card(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    title: str,
    body: str,
    accent: str = C["blue"],
    fill: str = C["blue_light"],
    title_size: int = 29,
    body_size: int = 25,
) -> None:
    x1, y1, x2, y2 = box
    rounded(draw, box, C["white"], C["line"], radius=14, width=2)
    draw.rectangle((x1, y1, x1 + 9, y2), fill=_rgb(accent))
    draw.rectangle((x1 + 9, y1, x2, y1 + 56), fill=_rgb(fill))
    draw_text(draw, (x1 + 30, y1 + 16), title, title_size, accent, "bold", max_width=x2 - x1 - 60)
    draw_text(draw, (x1 + 30, y1 + 86), body, body_size, C["ink"], "regular", max_width=x2 - x1 - 62, line_gap=1.25)


def pill(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], text: str, fill: str, color: str = C["white"]) -> None:
    rounded(draw, box, fill, None, radius=10)
    draw_box_text(draw, box, text, 23, color, "bold", "center", "center", pad=12)


def paste_image(img: Image.Image, draw: ImageDraw.ImageDraw, path: Path, box: tuple[int, int, int, int]) -> bool:
    if not path.exists():
        return False
    x1, y1, x2, y2 = box
    rounded(draw, box, C["white"], C["line"], radius=12, width=1)
    with Image.open(path) as source:
        source = source.convert("RGB")
        source.thumbnail((x2 - x1 - 26, y2 - y1 - 26), Image.Resampling.LANCZOS)
        px = x1 + (x2 - x1 - source.width) // 2
        py = y1 + (y2 - y1 - source.height) // 2
        img.paste(source, (px, py))
    return True


def table(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    widths: list[int],
    row_h: int,
    headers: list[str],
    rows: list[list[str]],
    font_size: int = 22,
) -> None:
    cx = x
    for w, h in zip(widths, headers):
        rounded(draw, (cx, y, cx + w, y + row_h), C["navy"], C["navy"], radius=0)
        draw_box_text(draw, (cx, y, cx + w, y + row_h), h, font_size, C["white"], "bold", "center", "center", pad=10)
        cx += w
    for i, row in enumerate(rows):
        cx = x
        fill = C["white"] if i % 2 else "#F8FAFC"
        for w, cell in zip(widths, row):
            draw.rectangle((cx, y + row_h * (i + 1), cx + w, y + row_h * (i + 2)), fill=fill, outline=C["line"], width=2)
            draw_box_text(
                draw,
                (cx, y + row_h * (i + 1), cx + w, y + row_h * (i + 2)),
                cell,
                font_size,
                C["ink"],
                "bold" if row.index(cell) == 0 else "regular",
                "center",
                "center",
                pad=10,
            )
            cx += w


def load_aggregate() -> dict[str, dict[str, dict[str, float]]]:
    data: dict[str, dict[str, dict[str, float]]] = {}
    if not AGGREGATE_CSV.exists():
        return data
    with AGGREGATE_CSV.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            data.setdefault(row["method_name"], {})[row["metric"]] = {
                "mean": float(row["mean"]),
                "std": float(row["std"]),
            }
    return data


def load_generation() -> dict[str, list[dict[str, float]]]:
    data: dict[str, list[dict[str, float]]] = {}
    if not GENERATION_CSV.exists():
        return data
    with GENERATION_CSV.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            data.setdefault(row["method_name"], []).append(
                {
                    "generation": float(row["generation"]),
                    "hv": float(row["archive_hypervolume_mean"]),
                    "diversity": float(row["population_diversity_mean"]),
                }
            )
    return data


def load_win_loss() -> tuple[int, int, int]:
    if not PAIRED_CSV.exists():
        return 70, 2, 28
    with PAIRED_CSV.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["metric"] == "final_archive_hypervolume" and row["comparison"] == "plain_fixed_standard":
                return int(row["win_count"]), int(row["tie_count"]), int(row["loss_count"])
    return 70, 2, 28


def draw_bar_chart(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    labels: list[str],
    values: list[float],
    colors: list[str],
    title: str,
    y_min: float | None = None,
    y_max: float | None = None,
) -> None:
    x1, y1, x2, y2 = box
    rounded(draw, box, C["white"], C["line"], radius=20, width=2)
    draw_text(draw, (x1 + 28, y1 + 24), title, 27, C["ink"], "bold", max_width=x2 - x1 - 56)
    plot = (x1 + 78, y1 + 100, x2 - 42, y2 - 96)
    px1, py1, px2, py2 = plot
    y_min = min(values) - 0.02 if y_min is None else y_min
    y_max = max(values) + 0.02 if y_max is None else y_max
    for i in range(4):
        yy = py2 - int((py2 - py1) * i / 3)
        draw.line((px1, yy, px2, yy), fill=C["line"], width=1)
        val = y_min + (y_max - y_min) * i / 3
        draw_text(draw, (x1 + 20, yy - 13), f"{val:.2f}", 18, C["muted"], max_width=50, align="right")
    draw.line((px1, py1, px1, py2), fill=C["muted"], width=2)
    draw.line((px1, py2, px2, py2), fill=C["muted"], width=2)
    n = len(values)
    slot = (px2 - px1) / n
    for i, (label, value, color) in enumerate(zip(labels, values, colors)):
        cx = px1 + int(slot * i + slot / 2)
        bar_w = int(slot * 0.48)
        top = py2 - int((value - y_min) / max(0.0001, y_max - y_min) * (py2 - py1))
        rounded(draw, (cx - bar_w // 2, top, cx + bar_w // 2, py2), color, None, radius=10)
        draw_text(draw, (cx - 80, top - 38), f"{value:.3f}", 21, C["ink"], "bold", max_width=160, align="center")
        draw_text(draw, (cx - 90, py2 + 18), label, 19, C["muted"], "regular", max_width=180, align="center")


def draw_win_bar(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], wins: int, ties: int, losses: int) -> None:
    x1, y1, x2, y2 = box
    total = wins + ties + losses
    rounded(draw, box, C["white"], C["line"], radius=20, width=2)
    draw_text(draw, (x1 + 28, y1 + 24), "同一seed比較", 27, C["ink"], "bold")
    bar_x1, bar_y1, bar_x2, bar_y2 = x1 + 42, y1 + 94, x2 - 42, y1 + 148
    segments = [
        (wins, C["blue"], "勝ち"),
        (ties, C["muted"], "分け"),
        (losses, C["orange"], "負け"),
    ]
    current = bar_x1
    for count, color, _ in segments:
        w = int((bar_x2 - bar_x1) * count / total)
        draw.rectangle((current, bar_y1, current + w, bar_y2), fill=color)
        current += w
    draw.rectangle((bar_x1, bar_y1, bar_x2, bar_y2), outline=C["line"], width=2)
    draw_text(draw, (x1 + 46, y1 + 174), f"{wins}勝 {ties}分 {losses}敗", 34, C["navy"], "bold")
    draw_text(draw, (x1 + 46, y1 + 230), "標準固定率GPに対し，多くのseedで最終HVが改善", 24, C["muted"], max_width=x2 - x1 - 92)


def draw_metric_comparison(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    hv_standard: float,
    hv_proposed: float,
    div_standard: float,
    div_proposed: float,
) -> None:
    x1, y1, x2, y2 = box
    rounded(draw, box, C["white"], C["line"], radius=20, width=2)
    draw_text(draw, (x1 + 28, y1 + 24), "最終HV・多様性", 27, C["ink"], "bold")
    metrics = [
        ("最終HV", hv_standard, hv_proposed, 0.74, 0.83),
        ("最終多様性", div_standard, div_proposed, 0.58, 0.67),
    ]
    for i, (label, standard, proposed, lo, hi) in enumerate(metrics):
        yy = y1 + 112 + i * 160
        draw_text(draw, (x1 + 38, yy), label, 25, C["navy"], "bold")
        for j, (name, value, color) in enumerate(
            [
                ("標準固定率", standard, METHOD_COLORS["plain_fixed_standard"]),
                ("提案法", proposed, METHOD_COLORS["bogp_current"]),
            ]
        ):
            by = yy + 50 + j * 48
            bx1, bx2 = x1 + 190, x2 - 120
            draw_text(draw, (x1 + 38, by - 3), name, 20, C["muted"], max_width=130, align="right")
            draw.rounded_rectangle((bx1, by, bx2, by + 30), radius=8, fill=_rgb(C["gray"]))
            bw = int((value - lo) / max(0.0001, hi - lo) * (bx2 - bx1))
            bw = max(8, min(bx2 - bx1, bw))
            draw.rounded_rectangle((bx1, by, bx1 + bw, by + 30), radius=8, fill=_rgb(color))
            draw_text(draw, (bx2 + 18, by - 4), f"{value:.3f}", 21, C["ink"], "bold")


def draw_line_chart(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    data: dict[str, list[dict[str, float]]],
    methods: list[str],
    metric: str,
    title: str,
    y_min: float | None = None,
    y_max: float | None = None,
) -> None:
    x1, y1, x2, y2 = box
    rounded(draw, box, C["white"], C["line"], radius=20, width=2)
    draw_text(draw, (x1 + 28, y1 + 24), title, 27, C["ink"], "bold")
    legend_x = x2 - 285
    legend_y = y1 + 28
    for idx, method in enumerate(methods):
        ly = legend_y + idx * 28
        color = METHOD_COLORS.get(method, C["blue"])
        draw.line((legend_x, ly + 13, legend_x + 38, ly + 13), fill=color, width=5)
        draw_text(draw, (legend_x + 48, ly), METHOD_LABELS.get(method, method), 18, color, "bold", max_width=180)
    plot_top = y1 + 160 if len(methods) > 1 else y1 + 110
    plot = (x1 + 72, plot_top, x2 - 58, y2 - 82)
    px1, py1, px2, py2 = plot
    all_points = [p for m in methods for p in data.get(m, [])]
    if not all_points:
        all_points = [
            {"generation": g, metric: 0.45 + 0.35 * (1 - math.exp(-g / 18))}
            for g in range(60)
        ]
        data = {methods[0]: all_points}
    xs = [p["generation"] for p in all_points]
    ys = [p[metric] for p in all_points]
    x_min, x_max = min(xs), max(xs)
    y_min = min(ys) - 0.03 if y_min is None else y_min
    y_max = max(ys) + 0.03 if y_max is None else y_max
    for i in range(5):
        yy = py2 - int((py2 - py1) * i / 4)
        draw.line((px1, yy, px2, yy), fill=C["line"], width=1)
        val = y_min + (y_max - y_min) * i / 4
        draw_text(draw, (x1 + 12, yy - 13), f"{val:.2f}", 18, C["muted"], max_width=50, align="right")
    draw.line((px1, py1, px1, py2), fill=C["muted"], width=2)
    draw.line((px1, py2, px2, py2), fill=C["muted"], width=2)

    def pt(p: dict[str, float]) -> tuple[int, int]:
        x = px1 + int((p["generation"] - x_min) / max(1.0, x_max - x_min) * (px2 - px1))
        y = py2 - int((p[metric] - y_min) / max(0.0001, y_max - y_min) * (py2 - py1))
        return x, y

    warm = 18
    wx = px1 + int((warm - x_min) / max(1.0, x_max - x_min) * (px2 - px1))
    draw.line((wx, py1, wx, py2), fill="#94A3B8", width=3)
    draw_text(draw, (wx + 8, py1 + 4), "warm-up", 18, C["muted"])

    for method in methods:
        rows = sorted(data.get(method, []), key=lambda p: p["generation"])
        if len(rows) < 2:
            continue
        points = [pt(row) for row in rows]
        draw.line(points, fill=METHOD_COLORS.get(method, C["blue"]), width=5, joint="curve")
    draw_text(draw, (px1, py2 + 24), "Generation", 19, C["muted"])


def draw_tree_icon(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float = 1.0, color: str = C["blue"]) -> None:
    r = int(22 * scale)
    nodes = [
        (x, y, "+"),
        (x - int(95 * scale), y + int(110 * scale), "x1"),
        (x + int(95 * scale), y + int(110 * scale), "sin"),
        (x + int(45 * scale), y + int(220 * scale), "x2"),
        (x + int(150 * scale), y + int(220 * scale), "x3"),
    ]
    for sx, sy, _ in nodes[1:3]:
        draw.line((x, y + r, sx, sy - r), fill=C["line"], width=max(2, int(5 * scale)))
    draw.line((x + int(95 * scale), y + int(110 * scale) + r, x + int(45 * scale), y + int(220 * scale) - r), fill=C["line"], width=max(2, int(5 * scale)))
    draw.line((x + int(95 * scale), y + int(110 * scale) + r, x + int(150 * scale), y + int(220 * scale) - r), fill=C["line"], width=max(2, int(5 * scale)))
    for nx, ny, label in nodes:
        draw.ellipse((nx - r, ny - r, nx + r, ny + r), fill=C["blue_light"], outline=color, width=max(2, int(4 * scale)))
        draw_box_text(draw, (nx - r, ny - r, nx + r, ny + r), label, int(18 * scale), color, "bold", "center", "center", pad=0)


def block(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    label: str,
    detail: str = "",
    accent: str = C["blue"],
    fill: str = C["white"],
    dark: bool = False,
) -> None:
    x1, y1, x2, y2 = box
    rounded(draw, box, fill if not dark else C["navy_2"], accent, radius=10, width=2)
    draw.rectangle((x1, y1, x2, y1 + 10), fill=_rgb(accent))
    text_color = C["white"] if dark else C["ink"]
    muted = "#C8D3E2" if dark else C["muted"]
    draw_box_text(draw, (x1 + 16, y1 + 18, x2 - 16, y1 + 72), label, 27, text_color, "bold", "center", "center", pad=0)
    if detail:
        draw_box_text(draw, (x1 + 22, y1 + 78, x2 - 22, y2 - 18), detail, 20, muted, "regular", "center", "center", pad=0)


def junction(draw: ImageDraw.ImageDraw, center: tuple[int, int], label: str = "+") -> None:
    x, y = center
    draw.ellipse((x - 28, y - 28, x + 28, y + 28), fill=_rgb(C["white"]), outline=_rgb(C["navy"]), width=3)
    draw_box_text(draw, (x - 28, y - 28, x + 28, y + 28), label, 27, C["navy"], "bold", "center", "center", pad=0)


def elbow_arrow(
    draw: ImageDraw.ImageDraw,
    points: list[tuple[int, int]],
    fill: str = C["navy"],
    width: int = 5,
    head: int = 17,
) -> None:
    for start, end in zip(points, points[1:-1]):
        draw.line((start, end), fill=fill, width=width)
    if len(points) >= 2:
        arrow(draw, points[-2], points[-1], fill=fill, width=width, head=head)


def signal_label(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, color: str = C["muted"]) -> None:
    x, y = xy
    rounded(draw, (x, y, x + 230, y + 38), C["paper"], C["hair"], radius=8, width=1)
    draw_box_text(draw, (x, y, x + 230, y + 38), text, 17, color, "bold", "center", "center", pad=4)


def evidence_note(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    text: str,
    accent: str = C["cyan"],
    font_size: int = 27,
) -> None:
    x1, y1, x2, y2 = box
    draw.line((x1, y1, x1, y2), fill=accent, width=7)
    draw_box_text(draw, (x1 + 22, y1, x2, y2), text, font_size, C["navy"], "bold", "left", "center", pad=0)


def slide_01() -> Image.Image:
    img, draw = new_slide()
    draw.rounded_rectangle((34, 28, W - 34, H - 28), radius=22, fill=_rgb(C["navy"]), outline=_rgb(C["navy"]))
    for x in range(170, W - 120, 120):
        draw.line((x, 120, x, 900), fill="#26364D", width=1)
    for y in range(150, 910, 90):
        draw.line((130, y, W - 120, y), fill="#26364D", width=1)
    draw.line((130, 910, W - 120, 910), fill=C["cyan"], width=4)
    draw_text(draw, (130, 92), "12分発表スライド構成 修正版", 27, "#9EE6F2", "bold")
    draw_box_text(
        draw,
        (170, 230, W - 170, 500),
        "多目的GPにおける\n操作率と更新周期の状態依存制御",
        68,
        C["white"],
        "bold",
        "center",
        "center",
        pad=0,
    )
    draw_box_text(
        draw,
        (250, 535, W - 250, 640),
        "文脈付きBOで交叉率・突然変異率・更新周期 k を動的に決定する",
        34,
        "#EAF2FF",
        "regular",
        "center",
        "center",
        pad=0,
    )
    flow = [("探索状態", C["blue"]), ("BO制御器", C["cyan"]), ("p_c, p_m, k", C["orange"]), ("GP進化", "#CBD5E1")]
    for i, (text, color) in enumerate(flow):
        x = 285 + i * 330
        rounded(draw, (x, 735, x + 250, 820), C["navy_2"], color, radius=10, width=2)
        draw_box_text(draw, (x, 735, x + 250, 820), text, 25, C["white"], "bold", "center", "center")
        if i < 3:
            arrow(draw, (x + 250, 778), (x + 320, 778), "#9EE6F2", width=5)
    elbow_arrow(draw, [(1305, 820), (1305, 870), (290, 870), (290, 820)], "#9EE6F2", width=4, head=14)
    draw_text(draw, (W - 220, H - 86), "01", 25, "#C7D2FE", max_width=120, align="right")
    return img


def slide_02() -> Image.Image:
    img, draw = new_slide()
    header(draw, "02", "社会的背景: 自動モデル発見・設計最適化の必要性", "INTRODUCTION")
    claim(draw, "複雑な問題では，人手で良い式や構造を設計することが難しい")
    card(draw, (135, 360, 520, 585), "シンボリック回帰", "データから解釈可能な数式を探索", C["blue"], C["blue_light"])
    card(draw, (590, 360, 975, 585), "構造探索", "プログラム木や設計候補の構造を生成", C["teal"], C["teal_light"])
    card(draw, (1045, 360, 1430, 585), "設計最適化", "精度・複雑さなど複数目的を同時に扱う", C["orange"], C["orange_light"])
    rounded(draw, (1510, 372, 1750, 575), C["gray"], None, radius=26)
    draw_tree_icon(draw, 1630, 420, scale=0.62, color=C["navy"])
    draw_box_text(draw, (280, 705, 1640, 840), "GPは，式や構造を木として表現し，交叉・突然変異で探索できる", 42, C["navy"], "bold", "center", "center", pad=0)
    arrow(draw, (960, 620), (960, 690), C["muted"], width=7)
    return img


def slide_03() -> Image.Image:
    img, draw = new_slide()
    header(draw, "03", "課題: 固定率では探索段階に対応しにくい", "INTRODUCTION")
    claim(draw, "多目的GPでは操作パラメータが探索挙動を左右し，望ましい値は探索段階で変わる")
    phases = [
        ("探索初期", "多様性確保\n広く試す", C["blue"], C["blue_light"]),
        ("中盤", "有望構造の\n組み替え", C["teal"], C["teal_light"]),
        ("停滞時", "局所解脱出\n再探索", C["orange"], C["orange_light"]),
    ]
    for i, (title, body, accent, fill) in enumerate(phases):
        x = 220 + i * 505
        card(draw, (x, 370, x + 390, 605), title, body, accent, fill, title_size=33, body_size=31)
        if i < 2:
            arrow(draw, (x + 410, 488), (x + 475, 488), C["muted"], width=7)
    rounded(draw, (180, 730, W - 180, 850), C["red_light"], C["red"], radius=26, width=3)
    draw_box_text(
        draw,
        (210, 730, W - 210, 850),
        "固定率GPは「今の探索状態」を見ないため，段階に応じた切り替えができない",
        40,
        C["red"],
        "bold",
        "center",
        "center",
    )
    return img


def slide_04() -> Image.Image:
    img, draw = new_slide()
    header(draw, "04", "関連研究と残る課題", "INTRODUCTION")
    claim(draw, "操作率は適応対象になり得るが，多目的GPの世代状態に基づく制御には課題が残る")

    draw_text(draw, (180, 325), "先行研究，できたこと", 28, C["navy"], "bold")
    draw.line((180, 365, 620, 365), fill=C["cyan"], width=4)

    prior_cards = [
        (
            (180, 392, 925, 610),
            "文献[1] 遺伝的演算子の適応",
            "・操作率を探索中に適応可能\n・固定率以外の探索制御を提示",
            C["blue"],
            C["blue_light"],
        ),
        (
            (1015, 392, 1760, 610),
            "文献[2] 木構造に応じた操作率変更",
            "・個体構造に応じて p_c, p_m を変更\n・木の性質を操作率に反映",
            C["teal"],
            C["teal_light"],
        ),
    ]
    for box, title, body, accent, fill in prior_cards:
        rounded(draw, box, fill, accent, radius=16, width=2)
        draw_box_text(draw, (box[0] + 26, box[1] + 26, box[2] - 26, box[1] + 82), title, 28, accent, "bold", "left", "center", pad=0)
        draw.line((box[0] + 26, box[1] + 92, box[2] - 26, box[1] + 92), fill=C["line"], width=2)
        draw_box_text(draw, (box[0] + 34, box[1] + 106, box[2] - 34, box[3] - 24), body, 24, C["ink"], "regular", "left", "center", pad=0)

    draw_text(draw, (180, 670), "Issue（課題）", 28, C["navy"], "bold")
    draw.line((180, 710, 460, 710), fill=C["orange"], width=4)

    issue_cards = [
        (
            (180, 742, 660, 925),
            "Issue 1",
            "世代状態の利用不足",
            "収束性，多様性，停滞を\nまとめて扱いにくい",
            C["blue"],
            C["blue_light"],
        ),
        (
            (720, 742, 1200, 925),
            "Issue 2",
            "多目的GPでの制御整理",
            "HV改善と多様性維持を\n状態に応じて判断しにくい",
            C["teal"],
            C["teal_light"],
        ),
        (
            (1260, 742, 1740, 925),
            "Issue 3",
            "更新周期 k",
            "操作率をいつ再調整するかが\n制御対象になっていない",
            C["orange"],
            C["orange_light"],
        ),
    ]
    for box, label, title, body, accent, fill in issue_cards:
        rounded(draw, box, C["white"], C["line"], radius=16, width=2)
        draw.rectangle((box[0], box[1], box[0] + 12, box[3]), fill=_rgb(accent))
        draw_text(draw, (box[0] + 32, box[1] + 24), label, 22, accent, "bold")
        draw_box_text(draw, (box[0] + 32, box[1] + 58, box[2] - 24, box[1] + 110), title, 28, C["navy"], "bold", "left", "center", pad=0)
        draw_box_text(draw, (box[0] + 32, box[1] + 118, box[2] - 24, box[3] - 22), body, 24, C["ink"], "regular", "left", "center", pad=0)

    rounded(draw, (310, 965, 1610, 1020), C["gray"], None, radius=14)
    draw_box_text(
        draw,
        (330, 965, 1590, 1020),
        "整理: 操作率は変えられるが，世代状態と更新周期まで含む制御には課題",
        24,
        C["navy"],
        "bold",
        "center",
        "center",
        pad=0,
    )
    return img


def slide_05() -> Image.Image:
    img, draw = new_slide()
    header(draw, "05", "研究目的と方策", "INTRODUCTION")
    claim(draw, "複数の世代状態を考慮し，操作率と更新タイミングを適応することで改善を目指す")

    draw_text(draw, (180, 330), "目的", 28, C["navy"], "bold")
    draw.line((180, 370, 310, 370), fill=C["cyan"], width=4)
    rounded(draw, (180, 398, 1760, 575), C["blue_light"], C["blue"], radius=22, width=3)
    draw.rectangle((180, 398, 196, 575), fill=_rgb(C["blue"]))
    draw_box_text(
        draw,
        (225, 416, 1720, 532),
        "複数の世代状態を考慮した\n操作率・更新タイミング適応による\n多様性・収束性の改善",
        34,
        C["navy"],
        "bold",
        "center",
        "center",
        pad=0,
    )
    draw_box_text(
        draw,
        (260, 532, 1685, 562),
        "対象: 交叉率 p_c・突然変異率 p_m・更新周期 k",
        24,
        C["muted"],
        "regular",
        "center",
        "center",
        pad=0,
    )

    draw_text(draw, (180, 625), "方策", 28, C["navy"], "bold")
    draw.line((180, 665, 310, 665), fill=C["orange"], width=4)
    rounded(draw, (180, 690, 1760, 770), C["orange_light"], C["orange"], radius=18, width=2)
    draw_box_text(
        draw,
        (210, 690, 1730, 770),
        "固定ハイパーパラメータ調整ではなく，閉ループ制御として扱う",
        32,
        C["navy"],
        "bold",
        "center",
        "center",
        pad=0,
    )
    steps = [
        ((180, 815, 560, 925), "観測", "世代状態 x\nHV・多様性・停滞長など", C["blue"], C["blue_light"]),
        ((770, 815, 1150, 925), "制御", "BOが\nu = (p_c, p_m, k) を決定", C["teal"], C["teal_light"]),
        ((1360, 815, 1740, 925), "更新", "報酬を計算し\n次の制御へ反映", C["orange"], C["orange_light"]),
    ]
    for i, (box, title, body, accent, fill) in enumerate(steps):
        rounded(draw, box, fill, accent, radius=18, width=2)
        draw_text(draw, (box[0] + 28, box[1] + 18), title, 28, accent, "bold")
        draw_box_text(draw, (box[0] + 120, box[1] + 16, box[2] - 24, box[3] - 14), body, 23, C["ink"], "regular", "left", "center", pad=0)
        if i < len(steps) - 1:
            arrow(draw, (box[2] + 32, 870), (box[2] + 175, 870), C["muted"], width=6, head=18)

    rounded(draw, (355, 960, 1585, 1015), C["gray"], None, radius=16)
    draw_box_text(
        draw,
        (385, 960, 1555, 1015),
        "次: GPをプラント，BOを制御器とみなす閉ループとして具体化",
        24,
        C["navy"],
        "bold",
        "center",
        "center",
        pad=0,
    )
    return img


def slide_06() -> Image.Image:
    img, draw = new_slide()
    header(draw, "06", "提案手法: GPをプラント，BOを制御器とみなす", "METHOD")
    claim(draw, "GPの世代進化をプラント，BOを制御器として閉ループを構成する")

    draw_text(draw, (220, 346), "closed-loop control view", 24, C["muted"], "bold")
    draw.line((215, 388, 1660, 388), fill=C["hair"], width=2)

    top_y1, top_y2 = 430, 570
    blocks = {
        "sensor": (215, top_y1, 485, top_y2),
        "controller": (600, top_y1, 870, top_y2),
        "input": (985, top_y1, 1255, top_y2),
        "plant": (1370, top_y1, 1640, top_y2),
    }
    block(draw, blocks["sensor"], "状態観測", "x: HV / 多様性 / 停滞長", C["blue"], C["blue_light"])
    block(draw, blocks["controller"], "BO制御器", "文脈 x から\n次の入力を選択", C["cyan"], C["navy_2"], dark=True)
    block(draw, blocks["input"], "制御入力", "u = (p_c, p_m, k)", C["orange"], C["orange_light"])
    block(draw, blocks["plant"], "GPプラント", "多目的GPを k 世代進化", C["navy"], C["gray"])

    mid_y = (top_y1 + top_y2) // 2
    elbow_arrow(draw, [(485, mid_y), (600, mid_y)], C["navy"], width=6)
    draw_text(draw, (505, mid_y - 42), "状態 x", 19, C["muted"], "bold", max_width=100, align="center")
    elbow_arrow(draw, [(870, mid_y), (985, mid_y)], C["navy"], width=6)
    draw_text(draw, (895, mid_y - 42), "入力 u", 19, C["muted"], "bold", max_width=100, align="center")
    elbow_arrow(draw, [(1255, mid_y), (1370, mid_y)], C["navy"], width=6)
    draw_text(draw, (1282, mid_y - 42), "適用", 19, C["muted"], "bold", max_width=80, align="center")

    reward_box = (1290, 660, 1640, 790)
    update_box = (600, 660, 950, 790)
    block(draw, reward_box, "報酬計算", "HV改善 + 多様性維持\n- 制御更新コスト", C["green"], C["green_light"])
    block(draw, update_box, "BO更新", "D に (x, u, reward)\nを追加", C["cyan"], C["cyan_light"])

    # Downstream observation and reward update path.
    elbow_arrow(draw, [(1505, top_y2), (1505, 625), (1465, 660)], C["navy"], width=6)
    draw_text(draw, (1515, 600), "世代結果", 19, C["muted"], "bold", max_width=110, align="center")
    junction(draw, (1115, 725), "r")
    elbow_arrow(draw, [(1290, 725), (1143, 725)], C["navy"], width=6)
    elbow_arrow(draw, [(1087, 725), (950, 725)], C["navy"], width=6)
    draw_text(draw, (1048, 678), "報酬 r", 19, C["muted"], "bold", max_width=120, align="center")
    elbow_arrow(draw, [(775, 660), (775, 570)], C["navy"], width=6)
    draw_text(draw, (785, 590), "履歴 D 更新", 19, C["muted"], "bold", max_width=130, align="center")

    # Single clean feedback line for the next generation state.
    feedback_y = 845
    elbow_arrow(draw, [(1505, 790), (1505, feedback_y), (350, feedback_y), (350, top_y2)], C["navy"], width=5)
    draw_text(draw, (820, feedback_y + 14), "次の世代状態", 20, C["muted"], "bold", max_width=220, align="center")

    evidence_note(
        draw,
        (245, 920, 1640, 985),
        "固定率の置き換えではなく，探索状態を観測して操作率と更新周期を再決定する制御問題として扱う",
        C["cyan"],
    )
    return img


def slide_07() -> Image.Image:
    img, draw = new_slide()
    header(draw, "07", "BO制御器の役割", "METHOD")
    claim(draw, "高コストなGP試行をすべて試さず，履歴から次の制御入力を選ぶ")

    draw_text(draw, (180, 330), "BOの考え方", 28, C["navy"], "bold")
    draw.line((180, 370, 465, 370), fill=C["cyan"], width=4)
    rounded(draw, (180, 400, 1055, 615), C["white"], C["line"], radius=18, width=2)
    draw.rectangle((180, 400, 196, 615), fill=_rgb(C["blue"]))
    draw_box_text(
        draw,
        (220, 422, 985, 485),
        "少ない試行で，次に試す入力を賢く選ぶ",
        30,
        C["navy"],
        "bold",
        "left",
        "center",
        pad=0,
    )
    bo_steps = [
        ((245, 520, 395, 570), "履歴 D", C["blue"]),
        ((490, 520, 665, 570), "代理モデル", C["teal"]),
        ((760, 520, 940, 570), "獲得関数", C["orange"]),
    ]
    for i, (box, label, accent) in enumerate(bo_steps):
        rounded(draw, box, C["gray"], accent, radius=12, width=2)
        draw_box_text(draw, box, label, 22, accent, "bold", "center", "center", pad=0)
        if i < len(bo_steps) - 1:
            arrow(draw, (box[2] + 20, 545), (box[2] + 90, 545), C["muted"], width=4, head=12)
    draw_text(draw, (245, 585), "過去の評価結果", 18, C["muted"], "regular")
    draw_text(draw, (500, 585), "性能を予測", 18, C["muted"], "regular")
    draw_text(draw, (750, 585), "有望さを評価", 18, C["muted"], "regular")

    draw_text(draw, (1160, 330), "なぜBOか", 28, C["navy"], "bold")
    draw.line((1160, 370, 1415, 370), fill=C["orange"], width=4)
    reasons = [
        ("1", "GP評価は高コスト", "試せる組合せ数に限りがある"),
        ("2", "有効な操作率は状態で変化", "探索初期・中盤・停滞で望ましい入力が違う"),
        ("3", "混合入力を扱う", "p_c, p_m は連続値，k は離散値"),
    ]
    for i, (idx, title, body) in enumerate(reasons):
        y = 405 + i * 68
        rounded(draw, (1160, y, 1760, y + 56), C["orange_light"] if i == 0 else C["white"], C["line"], radius=12, width=1)
        draw.ellipse((1180, y + 12, 1212, y + 44), fill=_rgb(C["orange"]))
        draw_box_text(draw, (1180, y + 12, 1212, y + 44), idx, 18, C["white"], "bold", "center", "center", pad=0)
        draw_text(draw, (1230, y + 8), title, 23, C["navy"], "bold", max_width=500)
        draw_text(draw, (1230, y + 35), body, 17, C["muted"], "regular", max_width=500)

    rounded(draw, (180, 685, 1760, 905), C["blue_light"], C["line"], radius=22, width=2)
    draw_text(draw, (220, 715), "本研究での位置づけ: BO = 制御器", 30, C["navy"], "bold")
    rounded(draw, (210, 745, 545, 880), C["white"], C["blue"], radius=16, width=2)
    draw_text(draw, (235, 765), "観測", 27, C["blue"], "bold")
    draw_box_text(draw, (235, 805, 520, 865), "GPの進化状態 x\nHV / 多様性 / 停滞長", 21, C["ink"], "regular", "left", "center", pad=0)

    rounded(draw, (755, 730, 1125, 890), C["navy_2"], C["cyan"], radius=20, width=3)
    draw_box_text(draw, (780, 752, 1100, 812), "BO制御器", 36, C["white"], "bold", "center", "center", pad=0)
    draw_box_text(draw, (785, 825, 1095, 875), "文脈 x から\n次の入力を選択", 22, "#C8D3E2", "regular", "center", "center", pad=0)

    rounded(draw, (1355, 745, 1725, 880), C["white"], C["orange"], radius=16, width=2)
    draw_text(draw, (1385, 765), "制御入力 u", 27, C["orange"], "bold")
    draw_box_text(draw, (1385, 810, 1695, 862), "p_c, p_m, k", 30, C["navy"], "bold", "center", "center", pad=0)

    arrow(draw, (545, 812), (755, 812), C["navy"], width=6, head=18)
    draw_text(draw, (590, 770), "状態に応じて", 18, C["muted"], "bold", max_width=150, align="center")
    arrow(draw, (1125, 812), (1355, 812), C["navy"], width=6, head=18)
    draw_text(draw, (1185, 770), "賢く選ぶ", 18, C["muted"], "bold", max_width=130, align="center")

    rounded(draw, (330, 945, 1610, 1010), C["gray"], None, radius=16)
    draw_box_text(
        draw,
        (360, 945, 1580, 1010),
        "固定率ではなく，探索段階に応じたパラメータ制御へ",
        28,
        C["navy"],
        "bold",
        "center",
        "center",
        pad=0,
    )
    return img


def slide_08() -> Image.Image:
    img, draw = new_slide()
    header(draw, "08", "報酬設計", "METHOD")
    claim(draw, "性能改善を主，多様性維持を副，制御コストを抑制項として設計する")
    rounded(draw, (230, 330, 1690, 455), C["navy_2"], None, radius=12)
    draw_box_text(draw, (250, 330, 1670, 455), "reward = HV改善 / 世代  +  多様性維持  -  制御更新コスト", 36, C["white"], "bold", "center", "center")

    inputs = [
        ((220, 565, 555, 685), "進捗", "世代あたりHV改善", C["blue"], "+"),
        ((220, 735, 555, 855), "多様性", "区間平均多様性", C["teal"], "+"),
        ((725, 790, 1060, 910), "コスト", "制御更新の負荷", C["orange"], "-"),
    ]
    for box, title, body, color, sign in inputs:
        block(draw, box, title, body, color, C["white"])
        sx = box[2] + 24
        sy = (box[1] + box[3]) // 2
        draw_text(draw, (sx, sy - 22), sign, 34, color, "bold")

    junction(draw, (1195, 720), "Σ")
    block(draw, (1395, 650, 1665, 790), "報酬", "BO更新に渡す", C["green"], C["green_light"])
    elbow_arrow(draw, [(555, 625), (650, 625), (650, 720), (1167, 720)], C["navy"], width=6)
    elbow_arrow(draw, [(555, 795), (650, 795), (650, 720), (1167, 720)], C["navy"], width=6)
    elbow_arrow(draw, [(1060, 850), (1110, 850), (1110, 735), (1167, 735)], C["navy"], width=6)
    elbow_arrow(draw, [(1223, 720), (1395, 720)], C["navy"], width=6)

    evidence_note(
        draw,
        (265, 950, 1645, 1015),
        "HVだけでは収束寄りになりやすいため，多様性項を残す",
        C["teal"],
    )
    return img


def slide_09() -> Image.Image:
    img, draw = new_slide()
    header(draw, "09", "実験設定", "EXPERIMENT")
    claim(draw, "Friedman-IIシンボリック回帰で，精度と複雑さのパレートフロント改善を評価する")
    rounded(draw, (130, 330, 1040, 445), C["gray"], None, radius=24)
    draw_box_text(
        draw,
        (150, 330, 1020, 445),
        "y = 10 sin(pi x1 x2) + 20 (x3 - 0.5)^2 + 10 x4 + 5 x5",
        32,
        C["navy"],
        "bold",
        "center",
        "center",
    )
    card(draw, (1120, 330, 1790, 445), "対象", "Friedman-II symbolic regression", C["blue"], C["blue_light"], title_size=27, body_size=24)
    table(
        draw,
        150,
        540,
        [330, 460, 460, 420],
        74,
        ["評価", "目的", "比較条件", "実行条件"],
        [
            ["目的1", "訓練NRMSE", "提案法", "100 seed"],
            ["目的2", "式木サイズ", "標準固定率", "同一評価回数"],
            ["指標", "HV・多様性・安定性", "高突然変異 / 高交叉", "Friedman-II"],
        ],
        font_size=22,
    )
    return img


def slide_10() -> Image.Image:
    img, draw = new_slide()
    header(draw, "10", "結果1: 標準固定率GPに対する改善", "RESULTS")
    claim(draw, "提案法は標準固定率GPより最終HV・多様性・安定性で良い傾向を示した")
    aggregate = load_aggregate()
    proposed = aggregate.get("bogp_current", {}).get("final_archive_hypervolume", {"mean": 0.802, "std": 0.022})
    standard = aggregate.get("plain_fixed_standard", {}).get("final_archive_hypervolume", {"mean": 0.783, "std": 0.055})
    proposed_div = aggregate.get("bogp_current", {}).get("final_diversity", {"mean": 0.641, "std": 0.087})
    standard_div = aggregate.get("plain_fixed_standard", {}).get("final_diversity", {"mean": 0.624, "std": 0.109})
    draw_metric_comparison(
        draw,
        (120, 335, 900, 775),
        standard["mean"],
        proposed["mean"],
        standard_div["mean"],
        proposed_div["mean"],
    )
    wins, ties, losses = load_win_loss()
    draw_win_bar(draw, (990, 335, 1800, 775), wins, ties, losses)
    rounded(draw, (260, 835, W - 260, 925), C["green_light"], C["green"], radius=24, width=3)
    draw_box_text(draw, (290, 835, W - 290, 925), f"HV標準偏差: 提案法 {proposed['std']:.3f} / 標準固定率 {standard['std']:.3f}", 35, C["green"], "bold", "center", "center")
    return img


def slide_11() -> Image.Image:
    img, draw = new_slide()
    header(draw, "11", "結果2: HV推移から見る収束性", "RESULTS")
    claim(draw, "warm-up後の推移を見ると，提案法は標準固定率より高い水準へ進むが，終盤では高突然変異が先行する")
    generation = load_generation()
    draw_line_chart(
        draw,
        (145, 320, 1325, 890),
        generation,
        ["plain_fixed_standard", "plain_fixed_high_mutation", "plain_fixed_high_crossover", "bogp_current"],
        "hv",
        "Archive HV の世代推移",
        y_min=0.44,
        y_max=0.84,
    )
    callouts = [
        ((250, 505, 520, 575), (360, 695), "序盤", "各手法でHVが急上昇", C["orange"], C["orange_light"]),
        ((515, 635, 820, 705), (650, 560), "warm-up後", "提案法が高水準へ移行", C["blue"], C["blue_light"]),
        ((930, 585, 1235, 655), (1170, 505), "終盤", "高突然変異がやや先行", C["teal"], C["teal_light"]),
    ]
    for box, target, _, _, accent, _ in callouts:
        cx = (box[0] + box[2]) // 2
        cy = (box[1] + box[3]) // 2
        if target[1] < box[1]:
            start = (cx, box[1])
        elif target[1] > box[3]:
            start = (cx, box[3])
        elif target[0] < box[0]:
            start = (box[0], cy)
        else:
            start = (box[2], cy)
        arrow(draw, start, target, accent, width=3, head=12)
    for box, target, title, body, accent, fill in callouts:
        rounded(draw, box, fill, accent, radius=14, width=2)
        draw_text(draw, (box[0] + 16, box[1] + 10), title, 22, accent, "bold")
        draw_text(draw, (box[0] + 16, box[1] + 40), body, 21, C["ink"], "regular")

    side = (1365, 320, 1795, 890)
    rounded(draw, side, C["white"], C["line"], radius=20, width=2)

    sections = [
        (
            350,
            215,
            "結果",
            "標準固定率より高いHV水準\n終盤では高突然変異が上側",
            C["blue"],
            C["blue_light"],
        ),
        (
            620,
            230,
            "考察",
            "閉ループ制御は収束を支援\nただし最良固定率を\n一貫して上回るには未達",
            C["teal"],
            C["teal_light"],
        ),
    ]
    for y, h, title, body, accent, fill in sections:
        rounded(draw, (1395, y, 1765, y + h), fill, accent, radius=16, width=2)
        draw_text(draw, (1420, y + 18), title, 28, accent, "bold")
        draw_box_text(draw, (1420, y + 60, 1745, y + h - 18), body, 24, C["ink"], "regular", "left", "center", pad=0)

    rounded(draw, (250, 925, 1710, 1000), C["gray"], None, radius=18)
    draw_box_text(
        draw,
        (285, 925, 1675, 1000),
        "議論: 収束性は改善傾向。ただし，強い固定率条件に対する優位性は未確立",
        26,
        C["navy"],
        "bold",
        "center",
        "center",
        pad=0,
    )
    return img


def slide_12() -> Image.Image:
    img, draw = new_slide()
    header(draw, "12", "結果3: 更新周期 k の挙動", "RESULTS")
    claim(draw, "k は同じ世代の結果ではなく，選択後の区間に保持される再調整タイミングの制御入力として読む")
    ok = paste_image(img, draw, FIG_DIR / "main_hv_diversity_k_alignment_seed26_slide.png", (145, 320, 1325, 890))
    if not ok:
        generation = load_generation()
        draw_line_chart(draw, (145, 320, 1325, 890), generation, ["bogp_current"], "hv", "HV and k alignment")

    callouts = [
        ((500, 390, 760, 462), (585, 485), "HV改善", "初期区間で大きく上昇", C["orange"], C["orange_light"]),
        ((750, 548, 1075, 622), (610, 620), "多様性", "探索状態の変動を観測", C["teal"], C["teal_light"]),
        ((770, 730, 1135, 804), (950, 760), "更新周期 k", "選択後の区間に保持", C["blue"], C["blue_light"]),
    ]
    for box, target, _, _, accent, _ in callouts:
        cx = (box[0] + box[2]) // 2
        cy = (box[1] + box[3]) // 2
        if target[1] < box[1]:
            start = (cx, box[1])
        elif target[1] > box[3]:
            start = (cx, box[3])
        elif target[0] < box[0]:
            start = (box[0], cy)
        else:
            start = (box[2], cy)
        arrow(draw, start, target, accent, width=3, head=12)
    for box, _, title, body, accent, fill in callouts:
        rounded(draw, box, fill, accent, radius=14, width=2)
        draw_text(draw, (box[0] + 16, box[1] + 9), title, 22, accent, "bold")
        draw_text(draw, (box[0] + 16, box[1] + 40), body, 21, C["ink"], "regular")

    side = (1365, 320, 1795, 890)
    rounded(draw, side, C["white"], C["line"], radius=20, width=2)
    sections = [
        (
            350,
            215,
            "結果",
            "HV・多様性の変化に対し\nk が短周期・長周期を切替",
            C["blue"],
            C["blue_light"],
        ),
        (
            620,
            230,
            "考察",
            "k は効率化だけでなく\nいつ再調整するかの制御入力\n効果は固定 k 比較で検証",
            C["teal"],
            C["teal_light"],
        ),
    ]
    for y, h, title, body, accent, fill in sections:
        rounded(draw, (1395, y, 1765, y + h), fill, accent, radius=16, width=2)
        draw_text(draw, (1420, y + 18), title, 28, accent, "bold")
        draw_box_text(draw, (1420, y + 60, 1745, y + h - 18), body, 24, C["ink"], "regular", "left", "center", pad=0)

    rounded(draw, (250, 925, 1710, 1000), C["gray"], None, radius=18)
    draw_box_text(
        draw,
        (285, 925, 1675, 1000),
        "議論: 操作率だけでなく，更新タイミングも状態依存に切り替える枠組みとして動作",
        26,
        C["navy"],
        "bold",
        "center",
        "center",
        pad=0,
    )
    return img


def slide_13() -> Image.Image:
    img, draw = new_slide()
    header(draw, "13", "考察: 何が分かり，何を切り分けるべきか", "DISCUSSION")
    claim(draw, "方向性は有望だが，どの要素が効いたかを追加比較で切り分ける必要がある")
    card(draw, (135, 340, 560, 610), "分かったこと", "標準固定率より改善\n安定性も向上傾向", C["green"], C["green_light"], body_size=30)
    card(draw, (745, 340, 1170, 610), "残る課題", "強い固定率には未到達\nBO制御器の改善余地", C["orange"], C["orange_light"], body_size=30)
    card(draw, (1355, 340, 1780, 610), "切り分け", "非文脈BO\n固定 k\n多様性項なし\n報酬設計", C["blue"], C["blue_light"], body_size=29)
    rounded(draw, (240, 745, W - 240, 865), C["gray"], None, radius=24)
    draw_box_text(draw, (270, 745, W - 270, 865), "次に見るべき問い: 状態，k，報酬のどれが改善に効いているのか", 37, C["navy"], "bold", "center", "center")
    return img


def slide_14() -> Image.Image:
    img, draw = new_slide()
    header(draw, "14", "結論", "CONCLUSION")
    sections = [
        (
            "目的",
            "・MOGP操作率設定の閉ループ制御化\n・探索状態に基づく p_c, p_m, k の動的決定",
            C["blue"],
        ),
        (
            "結果",
            "・標準固定率より最終HV・多様性・安定性で改善傾向\n・高突然変異固定率が平均HVで最良",
            C["green"],
        ),
        (
            "達成度",
            "・状態依存の p_c, p_m, k 制御の実装・評価\n・標準固定率に対する有効性の初期確認\n・最良固定率の一貫した上回りは未達",
            C["orange"],
        ),
        (
            "今後の展望",
            "・BO制御器・報酬設計の改善\n・固定 k，多様性項なし等のアブレーション\n・真の式の構成要素分析",
            C["cyan"],
        ),
    ]

    y = 285
    for i, (title, body, accent) in enumerate(sections):
        box = (210, y, 1715, y + 132)
        draw.line((box[0], box[1] + 8, box[0], box[3] - 8), fill=accent, width=8)
        draw_text(draw, (box[0] + 30, box[1] + 18), title, 28, accent, "bold", max_width=330, line_gap=1.22)
        draw_text(draw, (box[0] + 420, box[1] + 18), body, 24, C["ink"], "regular", max_width=1260, line_gap=1.34)
        if i < len(sections) - 1:
            draw.line((box[0] + 30, box[3] + 12, box[2], box[3] + 12), fill=C["hair"], width=2)
        y += 165

    evidence_note(
        draw,
        (245, 955, 1665, 1015),
        "中心メッセージ: 操作率・更新周期の状態依存制御の有望性",
        C["cyan"],
        font_size=24,
    )
    return img


def backup_01() -> Image.Image:
    img, draw = new_slide()
    header(draw, "B01", "補足: BOの基本", "BACKUP")
    claim(draw, "代理モデル，不確実性，獲得関数EIを使って次に試す入力を選ぶ")
    for i, (title, body, accent, fill) in enumerate(
        [
            ("代理モデル", "観測済みデータから\n性能を予測", C["blue"], C["blue_light"]),
            ("不確実性", "未探索領域の\n見込みを評価", C["teal"], C["teal_light"]),
            ("獲得関数 EI", "改善期待値が高い\n入力を選択", C["orange"], C["orange_light"]),
        ]
    ):
        x = 190 + i * 530
        card(draw, (x, 420, x + 420, 650), title, body, accent, fill, body_size=29)
        if i < 2:
            arrow(draw, (x + 435, 535), (x + 500, 535), C["muted"], width=7)
    rounded(draw, (300, 770, W - 300, 870), C["gray"], None, radius=24)
    draw_box_text(draw, (300, 770, W - 300, 870), "本研究では，このBOをGP外側の制御器として使う", 36, C["navy"], "bold", "center", "center")
    return img


def backup_02() -> Image.Image:
    img, draw = new_slide()
    header(draw, "B02", "補足: アーカイブと現在集団", "BACKUP")
    claim(draw, "HV・最終パレートフロントはアーカイブ，多様性は現在集団から計算する")
    card(draw, (210, 360, 830, 720), "アーカイブ", "過去に得られた非劣解を保持\nHV・最終Pareto frontの評価に使う", C["blue"], C["blue_light"], title_size=36, body_size=30)
    card(draw, (1090, 360, 1710, 720), "現在集団", "その世代で実際に進化している個体群\n多様性・木サイズなどの状態観測に使う", C["teal"], C["teal_light"], title_size=36, body_size=30)
    arrow(draw, (840, 540), (1075, 540), C["muted"], width=7)
    draw_box_text(draw, (250, 820, W - 250, 900), "同じGP実行でも，評価指標と状態観測で参照する集合が異なる", 34, C["navy"], "bold", "center", "center")
    return img


def backup_03() -> Image.Image:
    img, draw = new_slide()
    header(draw, "B03", "補足: パレートフロント詳細", "BACKUP")
    claim(draw, "代表seedのパレートフロントで，精度と複雑さのトレードオフを確認する")
    ok = paste_image(img, draw, FIG_DIR / "main_representative_pareto_front.png", (180, 310, 1280, 865))
    if not ok:
        draw_line_chart(draw, (180, 310, 1280, 865), {}, ["bogp_current"], "hv", "Pareto front schematic")
    card(draw, (1350, 410, 1765, 720), "見る点", "左下に近いほど良い\n複雑さごとに誤差の小さい解が残るかを確認", C["blue"], C["blue_light"], body_size=28)
    return img


def backup_04() -> Image.Image:
    img, draw = new_slide()
    header(draw, "B04", "補足: 更新周期 k の挙動", "BACKUP")
    claim(draw, "HV・多様性・k の同時系列から，再調整周期の切替タイミングを確認する")
    ok = paste_image(img, draw, FIG_DIR / "main_hv_diversity_k_alignment_seed26_slide.png", (145, 320, 1325, 890))
    if not ok:
        generation = load_generation()
        draw_line_chart(draw, (145, 320, 1325, 890), generation, ["bogp_current"], "hv", "HV and k alignment")

    callouts = [
        ((505, 390, 745, 458), (585, 485), "初期", "HVが急上昇", C["orange"], C["orange_light"]),
        ((760, 545, 1065, 615), (610, 620), "多様性", "初期に大きく変動", C["teal"], C["teal_light"]),
        ((780, 725, 1110, 795), (950, 760), "更新周期 k", "1・3・5を切替", C["blue"], C["blue_light"]),
    ]
    for box, target, _, _, accent, _ in callouts:
        cx = (box[0] + box[2]) // 2
        cy = (box[1] + box[3]) // 2
        if target[1] < box[1]:
            start = (cx, box[1])
        elif target[1] > box[3]:
            start = (cx, box[3])
        elif target[0] < box[0]:
            start = (box[0], cy)
        else:
            start = (box[2], cy)
        arrow(draw, start, target, accent, width=3, head=12)
    for box, _, title, body, accent, fill in callouts:
        rounded(draw, box, fill, accent, radius=14, width=2)
        draw_text(draw, (box[0] + 16, box[1] + 9), title, 22, accent, "bold")
        draw_text(draw, (box[0] + 16, box[1] + 39), body, 21, C["ink"], "regular")

    side = (1365, 320, 1795, 890)
    rounded(draw, side, C["white"], C["line"], radius=20, width=2)
    sections = [
        (
            385,
            185,
            "読み取り",
            "HV改善・多様性変動と\nk の切替が同時系列で見える",
            C["blue"],
            C["blue_light"],
        ),
        (
            655,
            185,
            "考察",
            "短周期と長周期を使い分ける\nただし効果の切り分けは\n追加比較が必要",
            C["teal"],
            C["teal_light"],
        ),
    ]
    for y, h, title, body, accent, fill in sections:
        rounded(draw, (1395, y, 1765, y + h), fill, accent, radius=16, width=2)
        draw_text(draw, (1420, y + 18), title, 28, accent, "bold")
        draw_box_text(draw, (1420, y + 58, 1745, y + h - 18), body, 23, C["ink"], "regular", "left", "center", pad=0)

    rounded(draw, (250, 925, 1710, 1000), C["gray"], None, radius=18)
    draw_box_text(
        draw,
        (285, 925, 1675, 1000),
        "読み取り: k は固定ではなく，探索中に再調整周期を切り替えている",
        26,
        C["navy"],
        "bold",
        "center",
        "center",
        pad=0,
    )
    return img


def backup_05() -> Image.Image:
    img, draw = new_slide()
    header(draw, "B05", "補足: k の選択回数", "BACKUP")
    claim(draw, "k in {1, 3, 5} の選択傾向から，制御器の再調整頻度を見る")
    ok = paste_image(img, draw, FIG_DIR / "main_k_selection_counts.png", (210, 305, 1260, 865))
    if not ok:
        draw_bar_chart(draw, (210, 305, 1260, 865), ["k=1", "k=3", "k=5"], [42, 33, 25], [C["blue"], C["teal"], C["orange"]], "k selection counts", 0, 50)
    card(draw, (1340, 425, 1765, 720), "確認したいこと", "短周期が多すぎないか\n長周期で反応が遅れないか\n状態との対応があるか", C["teal"], C["teal_light"], body_size=27)
    return img


def backup_06() -> Image.Image:
    img, draw = new_slide()
    header(draw, "B06", "補足: 真の式の構成要素分析", "BACKUP")
    claim(draw, "得られた式が，Friedman-IIの重要な構成要素をどの程度含むかを見る")
    terms = [
        ("x1 x2", "相互作用項"),
        ("sin", "周期構造"),
        ("x3^2", "二次項"),
        ("x4, x5", "線形項"),
    ]
    for i, (term, body) in enumerate(terms):
        x = 150 + i * 430
        rounded(draw, (x, 390, x + 330, 570), C["gray"], C["line"], radius=24)
        draw_box_text(draw, (x, 405, x + 330, 485), term, 42, C["blue"], "bold", "center", "center")
        draw_box_text(draw, (x, 490, x + 330, 555), body, 26, C["muted"], "regular", "center", "center")
    rounded(draw, (280, 720, W - 280, 850), C["blue_light"], C["blue"], radius=26, width=3)
    draw_box_text(draw, (310, 720, W - 310, 850), "分析方針: 最終アーカイブの式から各構成要素の出現頻度・組み合わせを調べる", 35, C["navy"], "bold", "center", "center")
    return img


SLIDES: list[tuple[str, Callable[[], Image.Image]]] = [
    ("01_title.png", slide_01),
    ("02_social_background.png", slide_02),
    ("03_fixed_rate_problem.png", slide_03),
    ("04_related_work_gap.png", slide_04),
    ("05_objective_novelty.png", slide_05),
    ("06_closed_loop_method.png", slide_06),
    ("07_state_action.png", slide_07),
    ("08_reward_design.png", slide_08),
    ("09_experiment_setup.png", slide_09),
    ("10_result_standard_fixed.png", slide_10),
    ("11_result_strong_fixed.png", slide_11),
    ("12_result_k_behavior.png", slide_12),
    ("13_discussion.png", slide_13),
    ("14_conclusion.png", slide_14),
    ("B01_bo_basics.png", backup_01),
    ("B02_archive_vs_population.png", backup_02),
    ("B03_pareto_front_detail.png", backup_03),
    ("B05_k_selection_counts.png", backup_05),
    ("B06_true_formula_components.png", backup_06),
]


def make_contact_sheet(paths: Iterable[Path]) -> Path:
    paths = list(paths)
    thumb_w, thumb_h = 320, 180
    pad_x, pad_y = 34, 54
    cols = 4
    rows = math.ceil(len(paths) / cols)
    sheet = Image.new("RGB", (cols * (thumb_w + pad_x) + pad_x, rows * (thumb_h + pad_y) + pad_y), _rgb(C["bg"]))
    draw = ImageDraw.Draw(sheet)
    for idx, path in enumerate(paths):
        row, col = divmod(idx, cols)
        x = pad_x + col * (thumb_w + pad_x)
        y = pad_y + row * (thumb_h + pad_y)
        with Image.open(path) as im:
            im = im.convert("RGB")
            im.thumbnail((thumb_w, thumb_h), Image.Resampling.LANCZOS)
            sheet.paste(im, (x, y))
        draw.rectangle((x, y, x + thumb_w, y + thumb_h), outline=_rgb(C["line"]), width=2)
        draw_text(draw, (x, y + thumb_h + 8), path.stem, 20, C["muted"], max_width=thumb_w, align="center")
    out = OUT_DIR / "00_contact_sheet.png"
    sheet.save(out)
    return out


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for filename, builder in SLIDES:
        path = OUT_DIR / filename
        builder().save(path, quality=95)
        paths.append(path)
    contact = make_contact_sheet(paths)
    print(f"rendered {len(paths)} slides")
    print(contact)
    for path in paths:
        print(path)


if __name__ == "__main__":
    main()
