#!/usr/bin/env python3
"""Build a 12-minute BOGP presentation as a PowerPoint deck.

This script intentionally uses only the Python standard library.  The normal
artifact-tool based presentation workflow was unavailable in this environment,
so the deck is generated as editable PresentationML directly.
"""

from __future__ import annotations

import datetime as _dt
import html
import os
from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "slides" / "BOGP_12min_presentation.pptx"
FIG_DIR = (
    ROOT
    / "outputs"
    / "main_bo_current_friedman"
    / "sr_alpha_friedman"
    / "main_bo_current_friedman_seed100_eval60_20260603"
    / "paper_labelled_figures"
)

FINAL_HV_FIG = FIG_DIR / "main_final_hv_diversity.png"
HV_PROGRESS_FIG = FIG_DIR / "main_hv_mean_progress.png"
PARETO_FIG = FIG_DIR / "main_representative_pareto_front.png"
K_ALIGNMENT_FIG = FIG_DIR / "main_hv_diversity_k_alignment_seed26.png"

EMU = 914400
SLIDE_W = int(13.333333 * EMU)
SLIDE_H = int(7.5 * EMU)


COLORS = {
    "bg": "F7F6F2",
    "paper": "FFFFFF",
    "dark": "2F3437",
    "ink": "252A2D",
    "muted": "687078",
    "line": "D8D3C8",
    "gold": "BFA46F",
    "gold_dark": "8D7447",
    "blue": "3B6EA8",
    "blue_light": "DCE8F4",
    "green": "3F8F72",
    "green_light": "DDEEE6",
    "orange": "C45A3A",
    "orange_light": "F2DFD7",
    "gray_light": "ECE9E1",
    "gray_mid": "C7C1B4",
    "white": "FFFFFF",
}


def emu(inches: float) -> int:
    return int(round(inches * EMU))


def esc(text: object) -> str:
    return html.escape(str(text), quote=False)


def srgb(color: str) -> str:
    return f'<a:solidFill><a:srgbClr val="{color}"/></a:solidFill>'


def no_fill() -> str:
    return "<a:noFill/>"


def line_xml(color: str | None = None, width: int = 10000, transparency: int | None = None) -> str:
    if color is None:
        return "<a:ln><a:noFill/></a:ln>"
    trans = ""
    if transparency is not None:
        trans = f'<a:alpha val="{transparency}"/>'
    return (
        f'<a:ln w="{width}">'
        f'<a:solidFill><a:srgbClr val="{color}">{trans}</a:srgbClr></a:solidFill>'
        "</a:ln>"
    )


def xfrm(x: float, y: float, w: float, h: float) -> str:
    return (
        "<a:xfrm>"
        f'<a:off x="{emu(x)}" y="{emu(y)}"/>'
        f'<a:ext cx="{emu(w)}" cy="{emu(h)}"/>'
        "</a:xfrm>"
    )


class SlideBuilder:
    def __init__(self, number: int, title: str | None = None, section: str = "BOGP"):
        self.number = number
        self.title = title
        self.section = section
        self.parts: list[str] = []
        self.rels: list[tuple[str, str, str]] = []
        self._id = 10
        self._img_id = 1
        self.media: list[tuple[str, Path]] = []
        self.background()

    def next_id(self) -> int:
        self._id += 1
        return self._id

    def background(self) -> None:
        self.rect(0, 0, 13.333333, 7.5, fill=COLORS["bg"], line=None)
        self.rect(0.18, 0.15, 12.96, 7.18, fill=COLORS["paper"], line=COLORS["line"], radius=False)

    def header(self) -> None:
        if self.title:
            self.text(0.62, 0.35, 9.3, 0.45, self.section, 9, COLORS["gold_dark"], bold=True)
            self.text(0.62, 0.74, 10.6, 0.55, self.title, 25, COLORS["ink"], bold=True)
            self.line(0.62, 1.24, 12.08, 0, color=COLORS["line"], width=7000)
            self.text(12.25, 7.06, 0.6, 0.25, f"{self.number:02d}", 9, COLORS["muted"], align="r")

    def rect(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        fill: str | None = None,
        line: str | None = COLORS["line"],
        radius: bool = True,
        alpha: int | None = None,
    ) -> None:
        sid = self.next_id()
        geom = "roundRect" if radius else "rect"
        fill_xml = no_fill() if fill is None else srgb(fill)
        if fill and alpha is not None:
            fill_xml = f'<a:solidFill><a:srgbClr val="{fill}"><a:alpha val="{alpha}"/></a:srgbClr></a:solidFill>'
        self.parts.append(
            f"""
<p:sp>
  <p:nvSpPr><p:cNvPr id="{sid}" name="Shape {sid}"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
  <p:spPr>{xfrm(x, y, w, h)}<a:prstGeom prst="{geom}"><a:avLst/></a:prstGeom>{fill_xml}{line_xml(line)}</p:spPr>
  <p:txBody><a:bodyPr/><a:lstStyle/><a:p/></p:txBody>
</p:sp>"""
        )

    def line(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        color: str = COLORS["line"],
        width: int = 12000,
        arrow: bool = False,
    ) -> None:
        sid = self.next_id()
        tail = '<a:tailEnd type="triangle"/>' if arrow else ""
        self.parts.append(
            f"""
<p:sp>
  <p:nvSpPr><p:cNvPr id="{sid}" name="Line {sid}"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
  <p:spPr>{xfrm(x, y, w, h)}<a:prstGeom prst="line"><a:avLst/></a:prstGeom>
    <a:ln w="{width}"><a:solidFill><a:srgbClr val="{color}"/></a:solidFill>{tail}</a:ln>
  </p:spPr>
  <p:txBody><a:bodyPr/><a:lstStyle/><a:p/></p:txBody>
</p:sp>"""
        )

    def text(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        text: str,
        size: int = 18,
        color: str = COLORS["ink"],
        bold: bool = False,
        fill: str | None = None,
        line: str | None = None,
        align: str = "l",
        valign: str = "t",
        font: str = "Yu Gothic",
        radius: bool = False,
        margin: int = 45720,
    ) -> None:
        sid = self.next_id()
        geom = "roundRect" if radius else "rect"
        fill_xml = no_fill() if fill is None else srgb(fill)
        align_map = {"l": "l", "c": "ctr", "r": "r"}
        anchor_map = {"t": "t", "m": "ctr", "b": "b"}
        p_xml = []
        lines = text.split("\n")
        bold_attr = ' b="1"' if bold else ""
        for line_text in lines:
            p_xml.append(
                f"""
<a:p>
  <a:pPr algn="{align_map.get(align, 'l')}"/>
  <a:r>
    <a:rPr lang="ja-JP" sz="{size * 100}"{bold_attr}>
      {srgb(color)}
      <a:latin typeface="{font}"/><a:ea typeface="{font}"/><a:cs typeface="{font}"/>
    </a:rPr>
    <a:t>{esc(line_text)}</a:t>
  </a:r>
</a:p>"""
            )
        self.parts.append(
            f"""
<p:sp>
  <p:nvSpPr><p:cNvPr id="{sid}" name="Text {sid}"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>
  <p:spPr>{xfrm(x, y, w, h)}<a:prstGeom prst="{geom}"><a:avLst/></a:prstGeom>{fill_xml}{line_xml(line)}</p:spPr>
  <p:txBody>
    <a:bodyPr wrap="square" anchor="{anchor_map.get(valign, 't')}" lIns="{margin}" rIns="{margin}" tIns="{margin}" bIns="{margin}"/>
    <a:lstStyle/>
    {''.join(p_xml)}
  </p:txBody>
</p:sp>"""
        )

    def card(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        title: str,
        body: str,
        color: str = COLORS["blue"],
        fill: str = COLORS["blue_light"],
    ) -> None:
        self.rect(x, y, w, h, fill=fill, line=color)
        self.text(x + 0.15, y + 0.12, w - 0.3, 0.33, title, 14, color, bold=True, fill=None)
        self.text(x + 0.15, y + 0.52, w - 0.3, h - 0.65, body, 15, COLORS["ink"], fill=None)

    def image(self, path: Path, x: float, y: float, w: float, h: float) -> None:
        if not path.exists():
            raise FileNotFoundError(path)
        sid = self.next_id()
        rid = f"rId{len(self.rels) + 2}"
        media_name = f"slide{self.number}_image{self._img_id}.png"
        self._img_id += 1
        self.media.append((media_name, path))
        self.rels.append(
            (
                rid,
                "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image",
                f"../media/{media_name}",
            )
        )
        self.parts.append(
            f"""
<p:pic>
  <p:nvPicPr><p:cNvPr id="{sid}" name="{media_name}"/><p:cNvPicPr/><p:nvPr/></p:nvPicPr>
  <p:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></p:blipFill>
  <p:spPr>{xfrm(x, y, w, h)}<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr>
</p:pic>"""
        )

    def xml(self) -> str:
        return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
       xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
       xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld>
    <p:spTree>
      <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
      <p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{SLIDE_W}" cy="{SLIDE_H}"/><a:chOff x="0" y="0"/><a:chExt cx="{SLIDE_W}" cy="{SLIDE_H}"/></a:xfrm></p:grpSpPr>
      {''.join(self.parts)}
    </p:spTree>
  </p:cSld>
  <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sld>"""

    def rels_xml(self) -> str:
        rels = [
            (
                "rId1",
                "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout",
                "../slideLayouts/slideLayout1.xml",
            )
        ] + self.rels
        body = "\n".join(
            f'<Relationship Id="{rid}" Type="{typ}" Target="{target}"/>' for rid, typ, target in rels
        )
        return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
{body}
</Relationships>"""


def slide_title() -> SlideBuilder:
    s = SlideBuilder(1, None)
    s.rect(0.55, 0.48, 12.25, 6.45, fill=COLORS["dark"], line=None, radius=False)
    s.rect(0.83, 0.78, 11.69, 5.87, fill="44494B", line=None, radius=False, alpha=65000)
    for x, y, w, h, a in [
        (9.3, 0.88, 3.0, 3.0, 18000),
        (0.95, 4.75, 2.2, 2.2, 12000),
        (6.2, 1.03, 1.1, 1.1, 16000),
    ]:
        s.rect(x, y, w, h, fill=COLORS["gold"], line=None, radius=True, alpha=a)
    s.text(0.95, 0.85, 4.0, 0.35, "12 min progress talk", 10, COLORS["gold"], bold=True)
    s.text(
        1.05,
        2.16,
        11.1,
        1.55,
        "多目的GPにおける\n操作率の閉ループ制御",
        36,
        COLORS["white"],
        bold=True,
        align="c",
        valign="m",
        margin=0,
    )
    s.text(
        2.0,
        3.92,
        9.4,
        0.58,
        "文脈付きベイズ最適化による交叉率・突然変異率・更新周期の動的調整",
        16,
        COLORS["white"],
        align="c",
        valign="m",
        margin=0,
    )
    s.line(3.1, 4.72, 7.1, 0, color=COLORS["gold"], width=14000)
    s.text(1.25, 5.82, 10.85, 0.45, "Friedman-II シンボリック回帰による初期検証", 13, "F2EFE6", align="c")
    s.text(1.1, 6.35, 11.1, 0.32, "Myojin / master_BOGP", 10, "D7D0BE", align="c")
    return s


def slide_overview() -> SlideBuilder:
    s = SlideBuilder(2, "研究の全体像", "INTRODUCTION")
    s.header()
    s.text(0.75, 1.55, 5.2, 0.6, "GPの探索状態を観測し，\n次の操作率をBOが決める", 24, COLORS["ink"], bold=True)
    boxes = [
        ("多目的GP", "精度と複雑さの\nPareto frontを探索", COLORS["green"], COLORS["green_light"], 0.85),
        ("状態観測", "HV・改善量・多様性\n木サイズ・停滞長", COLORS["blue"], COLORS["blue_light"], 3.8),
        ("BO制御器", "文脈 x に応じて\n行動 u を提案", COLORS["gold_dark"], "EFE7D4", 6.75),
        ("制御入力", "pc, pm, k を\n次の区間で保持", COLORS["orange"], COLORS["orange_light"], 9.7),
    ]
    for title, body, c, f, x in boxes:
        s.card(x, 3.0, 2.35, 1.65, title, body, c, f)
    for x in [3.23, 6.18, 9.13]:
        s.line(x, 3.82, 0.45, 0, color=COLORS["gray_mid"], width=15000, arrow=True)
    s.text(1.0, 5.45, 11.2, 0.6, "固定率の置き換えではなく，探索状態に応じた「操作強度」と「再調整タイミング」の制御", 18, COLORS["dark"], bold=True, align="c")
    return s


def slide_background() -> SlideBuilder:
    s = SlideBuilder(3, "背景: GPと操作率", "BACKGROUND")
    s.header()
    s.text(0.8, 1.55, 4.8, 0.5, "操作率は探索の性格を決める", 25, COLORS["ink"], bold=True)
    s.card(0.85, 2.35, 3.35, 1.8, "交叉率  pc", "既存の部分構造を組み替え，\n有望な解の組み合わせを探索する．", COLORS["blue"], COLORS["blue_light"])
    s.card(4.85, 2.35, 3.35, 1.8, "突然変異率  pm", "新しい部分構造を導入し，\n局所解からの脱出を助ける．", COLORS["orange"], COLORS["orange_light"])
    s.card(8.85, 2.35, 3.35, 1.8, "設定の影響", "多様性，収束速度，\n最終的な解集合品質に直結する．", COLORS["green"], COLORS["green_light"])
    s.text(1.05, 5.25, 11.0, 0.9, "しかし従来は，問題や探索段階が変わっても固定値のまま使われることが多い．", 22, COLORS["dark"], bold=True, align="c", fill=COLORS["gray_light"], radius=True)
    return s


def slide_fixed_problem() -> SlideBuilder:
    s = SlideBuilder(4, "固定率GPの問題", "BACKGROUND")
    s.header()
    s.text(0.85, 1.55, 5.2, 0.5, "探索段階ごとに望ましい操作は変わる", 24, COLORS["ink"], bold=True)
    y = 3.0
    s.line(1.2, y, 10.6, 0, COLORS["gray_mid"], width=12000)
    for x, label, desc in [
        (1.25, "探索初期", "広く試す\n多様性が重要"),
        (5.35, "中盤", "有望領域へ\n絞り込み"),
        (9.55, "終盤", "微調整と\n過収束回避"),
    ]:
        s.rect(x - 0.07, y - 0.07, 0.14, 0.14, fill=COLORS["gold"], line=None)
        s.text(x - 0.85, y + 0.28, 1.7, 0.3, label, 15, COLORS["gold_dark"], bold=True, align="c")
        s.text(x - 1.0, y + 0.68, 2.0, 0.75, desc, 16, COLORS["ink"], align="c")
    s.line(1.3, 5.75, 10.5, 0, COLORS["orange"], width=18000)
    s.text(4.25, 5.05, 4.7, 0.42, "固定率: 状態変化を見ない", 18, COLORS["orange"], bold=True, align="c")
    s.text(0.9, 6.38, 11.2, 0.35, "そこで，世代状態を見ながら操作率を変える閉ループ制御として設計する．", 17, COLORS["dark"], align="c")
    return s


def slide_mogp_difficulty() -> SlideBuilder:
    s = SlideBuilder(5, "多目的GPでは何が難しいか", "BACKGROUND")
    s.header()
    s.text(0.8, 1.55, 4.8, 0.5, "目標は単一の最良解ではない", 24, COLORS["ink"], bold=True)
    s.line(1.35, 5.95, 5.0, 0, COLORS["ink"], width=13000, arrow=True)
    s.line(1.35, 5.95, 0, -3.95, COLORS["ink"], width=13000, arrow=True)
    s.text(3.2, 6.18, 2.2, 0.3, "式木サイズ", 13, COLORS["muted"], align="c")
    s.text(0.35, 3.28, 1.3, 0.3, "誤差", 13, COLORS["muted"], align="c")
    for x, y, c in [(1.75, 4.9, COLORS["blue"]), (2.25, 4.1, COLORS["blue"]), (3.0, 3.28, COLORS["blue"]), (4.05, 2.7, COLORS["blue"]), (5.1, 2.28, COLORS["blue"])]:
        s.rect(x, y, 0.12, 0.12, fill=c, line=None)
    s.line(1.82, 4.95, 3.35, -2.6, COLORS["blue"], width=10000)
    s.text(2.95, 2.03, 3.2, 0.35, "Pareto front", 15, COLORS["blue"], bold=True)
    s.card(7.2, 2.05, 4.6, 1.1, "収束性", "誤差の小さい解へ近づく", COLORS["green"], COLORS["green_light"])
    s.card(7.2, 3.55, 4.6, 1.1, "多様性", "異なる複雑さ・構造の解を残す", COLORS["gold_dark"], "EFE7D4")
    s.text(7.35, 5.35, 4.4, 0.72, "この2つを同時に満たすため，操作率の制御が重要になる．", 18, COLORS["dark"], bold=True, align="c", fill=COLORS["gray_light"], radius=True)
    return s


def slide_objective() -> SlideBuilder:
    s = SlideBuilder(6, "研究目的", "INTRODUCTION")
    s.header()
    s.text(1.0, 1.75, 11.4, 1.6, "交叉率・突然変異率を探索状態に応じて動的に調整し，\n多目的GPの収束性と多様性を改善する", 28, COLORS["dark"], bold=True, align="c", valign="m")
    for x, title, body, c, f in [
        (1.15, "動的調整", "固定率ではなく\n状態を見て切り替える", COLORS["blue"], COLORS["blue_light"]),
        (4.95, "収束性", "パレートフロントを\nより良い領域へ進める", COLORS["green"], COLORS["green_light"]),
        (8.75, "多様性", "早期収束を避け\n解集合の広がりを保つ", COLORS["gold_dark"], "EFE7D4"),
    ]:
        s.card(x, 4.25, 2.95, 1.55, title, body, c, f)
    return s


def slide_closed_loop() -> SlideBuilder:
    s = SlideBuilder(7, "提案法の考え方", "METHOD")
    s.header()
    s.text(0.85, 1.55, 5.5, 0.5, "GPをプラント，BOを制御器とみなす", 24, COLORS["ink"], bold=True)
    s.card(1.1, 3.0, 3.0, 1.35, "GP Plant", "k世代だけ進化\n集団と指標を返す", COLORS["green"], COLORS["green_light"])
    s.card(8.95, 3.0, 3.0, 1.35, "BO Controller", "状態 x を入力し\n次の行動 u を提案", COLORS["blue"], COLORS["blue_light"])
    s.line(4.25, 3.62, 4.55, 0, COLORS["gray_mid"], width=17000, arrow=True)
    s.text(5.35, 3.2, 2.4, 0.35, "観測: HV, D, Lbar ...", 13, COLORS["muted"], align="c")
    s.line(8.78, 4.28, -4.55, 0, COLORS["orange"], width=17000, arrow=True)
    s.text(5.2, 4.42, 2.8, 0.35, "制御: pc, pm, k", 14, COLORS["orange"], bold=True, align="c")
    s.text(2.0, 5.85, 9.3, 0.62, "観測 → 制御 → 実行 → 評価 → 学習 を繰り返す閉ループ", 20, COLORS["dark"], bold=True, align="c", fill=COLORS["gray_light"], radius=True)
    return s


def slide_action() -> SlideBuilder:
    s = SlideBuilder(8, "提案法の制御入力", "METHOD")
    s.header()
    s.text(0.95, 1.7, 11.2, 0.75, "BOが決める行動:  uℓ = ( pc, pm, k )", 30, COLORS["dark"], bold=True, align="c")
    s.card(1.1, 3.1, 3.15, 1.75, "pc", "交叉率\n既存構造の組み替え強度", COLORS["blue"], COLORS["blue_light"])
    s.card(4.95, 3.1, 3.15, 1.75, "pm", "突然変異率\n新規構造の導入強度", COLORS["orange"], COLORS["orange_light"])
    s.card(8.8, 3.1, 3.15, 1.75, "k", "次回更新までの世代数\n再調整タイミング", COLORS["gold_dark"], "EFE7D4")
    s.text(1.4, 5.7, 10.6, 0.5, "新規性の軸: 「どの率にするか」だけでなく「いつ再調整するか」も制御する", 18, COLORS["dark"], bold=True, align="c")
    return s


def slide_state() -> SlideBuilder:
    s = SlideBuilder(9, "観測する状態", "METHOD")
    s.header()
    s.text(0.82, 1.55, 6.2, 0.5, "現在の探索状態を文脈ベクトルとしてBOに渡す", 23, COLORS["ink"], bold=True)
    cards = [
        ("世代進行率", "τ", COLORS["blue"], COLORS["blue_light"]),
        ("現在HV", "HV", COLORS["green"], COLORS["green_light"]),
        ("直近改善量", "ΔHV", COLORS["gold_dark"], "EFE7D4"),
        ("多様性", "D", COLORS["orange"], COLORS["orange_light"]),
        ("平均木サイズ", "Lbar", COLORS["blue"], COLORS["blue_light"]),
        ("停滞長", "s", COLORS["green"], COLORS["green_light"]),
    ]
    for i, (title, sym, c, f) in enumerate(cards):
        x = 0.95 + (i % 3) * 4.05
        y = 2.45 + (i // 3) * 1.75
        s.rect(x, y, 3.15, 1.25, fill=f, line=c)
        s.text(x + 0.15, y + 0.15, 2.85, 0.32, title, 13, c, bold=True)
        s.text(x + 0.15, y + 0.52, 2.85, 0.55, sym, 26, COLORS["dark"], bold=True, align="c")
    s.text(1.0, 6.05, 11.0, 0.45, "非文脈BOとの差は，この状態 xℓ を条件に含める点にある．", 17, COLORS["dark"], bold=True, align="c")
    return s


def slide_reward() -> SlideBuilder:
    s = SlideBuilder(10, "報酬設計", "METHOD")
    s.header()
    s.text(0.85, 1.55, 5.1, 0.5, "進捗・多様性・制御コストをまとめて評価する", 23, COLORS["ink"], bold=True)
    s.card(0.95, 2.55, 3.2, 1.45, "主項", "世代あたりHV改善\nΔHV rate", COLORS["green"], COLORS["green_light"])
    s.card(4.65, 2.55, 3.2, 1.45, "副項", "区間平均多様性\nDbar の維持", COLORS["blue"], COLORS["blue_light"])
    s.card(8.35, 2.55, 3.2, 1.45, "抑制項", "密な更新のコスト\nCk(k)", COLORS["orange"], COLORS["orange_light"])
    s.text(2.0, 4.65, 9.3, 0.8, "rℓ = 進捗 + 多様性維持 − 制御コスト", 27, COLORS["dark"], bold=True, align="c", fill=COLORS["gray_light"], radius=True)
    s.text(1.15, 6.0, 10.85, 0.35, "kが大きいほど有利にならないよう，区間総改善量ではなく世代あたり改善量を使う．", 15, COLORS["muted"], align="c")
    return s


def slide_algorithm() -> SlideBuilder:
    s = SlideBuilder(11, "アルゴリズムの流れ", "METHOD")
    s.header()
    steps = [
        ("1", "初期集団生成"),
        ("2", "状態 xℓ を観測"),
        ("3", "warm-up または BOで uℓ を選択"),
        ("4", "pc, pm を保持して k世代 GPを実行"),
        ("5", "区間統計 ΔHV rate, Dbar, Ck を取得"),
        ("6", "報酬 rℓ を計算し履歴 (x,u,r) に追加"),
    ]
    for i, (num, text) in enumerate(steps):
        y = 1.55 + i * 0.83
        s.rect(1.05, y, 0.55, 0.55, fill=COLORS["dark"], line=None)
        s.text(1.05, y + 0.02, 0.55, 0.32, num, 14, COLORS["white"], bold=True, align="c")
        s.rect(1.85, y, 10.6, 0.55, fill=COLORS["gray_light"], line=COLORS["line"])
        s.text(2.05, y + 0.08, 10.0, 0.28, text, 15, COLORS["ink"], bold=True)
    s.text(2.0, 6.75, 9.4, 0.35, "このループにより，BOはGPの状態変化に合わせて次の制御入力を学習する．", 15, COLORS["muted"], align="c")
    return s


def slide_problem() -> SlideBuilder:
    s = SlideBuilder(12, "実験問題: Friedman-II", "EXPERIMENT")
    s.header()
    s.text(0.82, 1.5, 6.0, 0.5, "真の関数が既知なシンボリック回帰ベンチマーク", 22, COLORS["ink"], bold=True)
    eq = "y = 10 sin(π x1 x2) + 20(x3 − 0.5)^2 + 10x4 + 5x5"
    s.text(0.95, 2.35, 11.4, 1.05, eq, 24, COLORS["dark"], bold=True, align="c", valign="m", fill=COLORS["gray_light"], radius=True)
    s.card(1.15, 4.15, 3.35, 1.35, "含まれる構造", "変数間相互作用\n三角関数・二次項・線形項", COLORS["blue"], COLORS["blue_light"])
    s.card(5.05, 4.15, 3.35, 1.35, "扱いやすさ", "5変数で可視化しやすく\n非線形性もある", COLORS["green"], COLORS["green_light"])
    s.card(8.95, 4.15, 3.35, 1.35, "注意", "真の式はデータ生成用であり\nGPには構造を与えない", COLORS["gold_dark"], "EFE7D4")
    return s


def slide_evaluation() -> SlideBuilder:
    s = SlideBuilder(13, "評価方針", "EXPERIMENT")
    s.header()
    s.text(0.85, 1.55, 6.0, 0.5, "真の式の完全復元ではなく，解集合の質を見る", 23, COLORS["ink"], bold=True)
    s.card(0.95, 2.55, 3.4, 1.4, "目的1", "訓練NRMSE\n予測誤差を小さくする", COLORS["blue"], COLORS["blue_light"])
    s.card(4.7, 2.55, 3.4, 1.4, "目的2", "式木サイズ\n複雑さを小さくする", COLORS["green"], COLORS["green_light"])
    s.card(8.45, 2.55, 3.4, 1.4, "評価", "最終アーカイブHV\n多様性・Pareto front", COLORS["gold_dark"], "EFE7D4")
    s.text(1.15, 5.15, 10.85, 0.75, "精度と複雑さのトレードオフが，固定率GPより良くなるかを検証する．", 22, COLORS["dark"], bold=True, align="c", fill=COLORS["gray_light"], radius=True)
    return s


def slide_conditions() -> SlideBuilder:
    s = SlideBuilder(14, "比較条件", "EXPERIMENT")
    s.header()
    s.text(0.85, 1.48, 5.0, 0.5, "提案法と固定率GPを同じ問題で比較", 23, COLORS["ink"], bold=True)
    headers = ["条件", "制御", "狙い"]
    rows = [
        ["BO current", "pc, pm, k をBOで更新", "提案法"],
        ["標準固定率", "pc=0.7, pm=0.2", "通常GPの基準"],
        ["高突然変異", "pm を高める", "多様性重視"],
        ["高交叉", "pc を高める", "組み替え重視"],
    ]
    x0, y0 = 0.85, 2.05
    widths = [2.75, 4.6, 4.05]
    for j, head in enumerate(headers):
        s.rect(x0 + sum(widths[:j]), y0, widths[j], 0.5, fill=COLORS["dark"], line=COLORS["dark"], radius=False)
        s.text(x0 + sum(widths[:j]) + 0.05, y0 + 0.07, widths[j] - 0.1, 0.25, head, 13, COLORS["white"], bold=True, align="c")
    for i, row in enumerate(rows):
        y = y0 + 0.55 + i * 0.6
        for j, cell in enumerate(row):
            fill = "F4F1EA" if i % 2 == 0 else COLORS["white"]
            s.rect(x0 + sum(widths[:j]), y, widths[j], 0.55, fill=fill, line=COLORS["line"], radius=False)
            s.text(x0 + sum(widths[:j]) + 0.08, y + 0.08, widths[j] - 0.16, 0.25, cell, 12, COLORS["ink"], bold=(j == 0), align="c")
    s.text(1.0, 5.35, 11.0, 0.55, "100 seed・warm-up 18世代 + 評価60世代で比較", 20, COLORS["dark"], bold=True, align="c", fill=COLORS["gray_light"], radius=True)
    return s


def slide_result_hv() -> SlideBuilder:
    s = SlideBuilder(15, "結果1: 最終HVと多様性", "RESULTS")
    s.header()
    s.image(FINAL_HV_FIG, 0.8, 1.47, 11.85, 5.15)
    s.text(1.0, 6.62, 11.0, 0.4, "提案法は標準固定率GPを上回り，高突然変異固定率に次ぐ水準を示した．", 16, COLORS["dark"], bold=True, align="c")
    return s


def slide_variability() -> SlideBuilder:
    s = SlideBuilder(16, "結果2: ばらつき", "RESULTS")
    s.header()
    s.text(0.85, 1.55, 6.5, 0.5, "最終HVの標準偏差を見ると，提案法は最も小さい", 23, COLORS["ink"], bold=True)
    data = [
        ("BO current", "0.022", COLORS["blue"], COLORS["blue_light"]),
        ("高突然変異", "0.030", COLORS["orange"], COLORS["orange_light"]),
        ("高交叉", "0.030", COLORS["green"], COLORS["green_light"]),
        ("標準固定率", "0.055", COLORS["gold_dark"], "EFE7D4"),
    ]
    for i, (name, val, c, f) in enumerate(data):
        x = 0.95 + i * 3.05
        s.rect(x, 2.65, 2.55, 2.45, fill=f, line=c)
        s.text(x + 0.15, 2.9, 2.25, 0.35, name, 15, c, bold=True, align="c")
        s.text(x + 0.15, 3.55, 2.25, 0.58, val, 34, COLORS["dark"], bold=True, align="c")
        s.text(x + 0.15, 4.38, 2.25, 0.3, "HV std.", 12, COLORS["muted"], align="c")
    s.text(1.2, 5.9, 10.8, 0.55, "平均性能だけでなく，seed間の安定性でも提案法に良い兆しがある．", 19, COLORS["dark"], bold=True, align="c", fill=COLORS["gray_light"], radius=True)
    return s


def slide_progress() -> SlideBuilder:
    s = SlideBuilder(17, "結果3: 世代推移", "RESULTS")
    s.header()
    s.image(HV_PROGRESS_FIG, 1.0, 1.42, 11.2, 5.55)
    return s


def slide_pareto() -> SlideBuilder:
    s = SlideBuilder(18, "結果4: Pareto front形状", "RESULTS")
    s.header()
    s.image(PARETO_FIG, 0.78, 1.42, 7.2, 5.5)
    s.card(8.35, 1.65, 3.65, 1.25, "見るべき点", "HVの数値だけでなく\n解集合の形を確認する", COLORS["blue"], COLORS["blue_light"])
    s.card(8.35, 3.25, 3.65, 1.25, "トレードオフ", "低複雑度・高精度・中間領域の\nどこを埋めるかが重要", COLORS["green"], COLORS["green_light"])
    s.card(8.35, 4.85, 3.65, 1.25, "考察", "提案法の評価には\n領域別の分析も必要", COLORS["gold_dark"], "EFE7D4")
    return s


def slide_k() -> SlideBuilder:
    s = SlideBuilder(19, "結果5: 更新周期 k の時系列", "RESULTS")
    s.header()
    s.image(K_ALIGNMENT_FIG, 0.75, 1.35, 7.55, 5.25)
    s.text(8.55, 1.55, 3.75, 0.75, "代表seedで\nHV・多様性・kを対応づける", 21, COLORS["dark"], bold=True, align="c", valign="m")
    s.card(8.65, 2.78, 3.55, 1.15, "読み方", "kは選択後の区間に\n保持される制御入力", COLORS["blue"], COLORS["blue_light"])
    s.card(8.65, 4.25, 3.55, 1.15, "考察", "HV上昇・停滞・多様性低下と\nk切替の対応を見る", COLORS["orange"], COLORS["orange_light"])
    s.text(8.6, 5.82, 3.55, 0.42, "回数だけでなく「いつ選ばれたか」が重要", 13, COLORS["muted"], align="c")
    return s


def slide_future() -> SlideBuilder:
    s = SlideBuilder(20, "考察と今後やること", "DISCUSSION")
    s.header()
    s.text(0.85, 1.45, 11.3, 0.6, "標準固定率GPには有効性を示したが，強い固定率条件を安定して上回るには改善が必要", 20, COLORS["dark"], bold=True, align="c")
    items = [
        ("1. BO制御器の改善", "報酬スケーリング，多様性項の重み，EI比較，warm-up設計を見直す．", COLORS["blue"], COLORS["blue_light"]),
        ("2. 比較実験の追加", "非文脈BO，固定k版，多様性項なし版で効果を切り分ける．", COLORS["green"], COLORS["green_light"]),
        ("3. 評価指標の拡張", "HVだけでなく，領域別Pareto評価，安定性，制御回数，計算コストを見る．", COLORS["gold_dark"], "EFE7D4"),
        ("4. 対象問題の拡張", "他のシンボリック回帰ベンチマークや構造探索問題へ適用する．", COLORS["orange"], COLORS["orange_light"]),
    ]
    for i, (title, body, c, f) in enumerate(items):
        x = 0.95 + (i % 2) * 6.1
        y = 2.25 + (i // 2) * 1.72
        s.card(x, y, 5.25, 1.28, title, body, c, f)
    s.text(1.25, 6.55, 10.85, 0.42, "次段階では「状態依存制御」と「更新周期制御」が本当に効く条件を明確にする．", 17, COLORS["dark"], bold=True, align="c")
    return s


SLIDE_BUILDERS = [
    slide_title,
    slide_overview,
    slide_background,
    slide_fixed_problem,
    slide_mogp_difficulty,
    slide_objective,
    slide_closed_loop,
    slide_action,
    slide_state,
    slide_reward,
    slide_algorithm,
    slide_problem,
    slide_evaluation,
    slide_conditions,
    slide_result_hv,
    slide_variability,
    slide_progress,
    slide_pareto,
    slide_k,
    slide_future,
]


def content_types(nslides: int) -> str:
    overrides = [
        '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>',
        '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>',
        '<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>',
        '<Override PartName="/ppt/presProps.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presProps+xml"/>',
        '<Override PartName="/ppt/viewProps.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.viewProps+xml"/>',
        '<Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>',
        '<Override PartName="/ppt/tableStyles.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.tableStyles+xml"/>',
        '<Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>',
        '<Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>',
    ]
    overrides += [
        f'<Override PartName="/ppt/slides/slide{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
        for i in range(1, nslides + 1)
    ]
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Default Extension="png" ContentType="image/png"/>
  {''.join(overrides)}
</Types>"""


def package_rels() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>"""


def presentation_xml(nslides: int) -> str:
    slide_ids = "\n".join(
        f'<p:sldId id="{255 + i}" r:id="rId{i + 1}"/>' for i in range(1, nslides + 1)
    )
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
                xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
                xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst>
  <p:sldIdLst>{slide_ids}</p:sldIdLst>
  <p:sldSz cx="{SLIDE_W}" cy="{SLIDE_H}" type="wide"/>
  <p:notesSz cx="6858000" cy="9144000"/>
  <p:defaultTextStyle>
    <a:defPPr><a:defRPr lang="ja-JP"><a:latin typeface="Yu Gothic"/><a:ea typeface="Yu Gothic"/></a:defRPr></a:defPPr>
  </p:defaultTextStyle>
</p:presentation>"""


def presentation_rels(nslides: int) -> str:
    rels = [
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>'
    ]
    rels += [
        f'<Relationship Id="rId{i + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide{i}.xml"/>'
        for i in range(1, nslides + 1)
    ]
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  {''.join(rels)}
</Relationships>"""


def master_xml() -> str:
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldMaster xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
             xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
             xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld><p:spTree>
    <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
    <p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{SLIDE_W}" cy="{SLIDE_H}"/><a:chOff x="0" y="0"/><a:chExt cx="{SLIDE_W}" cy="{SLIDE_H}"/></a:xfrm></p:grpSpPr>
  </p:spTree></p:cSld>
  <p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/>
  <p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst>
  <p:txStyles><p:titleStyle/><p:bodyStyle/><p:otherStyle/></p:txStyles>
</p:sldMaster>"""


def master_rels() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="../theme/theme1.xml"/>
</Relationships>"""


def layout_xml() -> str:
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldLayout xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
             xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
             xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" type="blank" preserve="1">
  <p:cSld name="Blank"><p:spTree>
    <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
    <p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{SLIDE_W}" cy="{SLIDE_H}"/><a:chOff x="0" y="0"/><a:chExt cx="{SLIDE_W}" cy="{SLIDE_H}"/></a:xfrm></p:grpSpPr>
  </p:spTree></p:cSld>
  <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sldLayout>"""


def layout_rels() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="../slideMasters/slideMaster1.xml"/>
</Relationships>"""


def theme_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="BOGP Theme">
  <a:themeElements>
    <a:clrScheme name="BOGP">
      <a:dk1><a:srgbClr val="252A2D"/></a:dk1><a:lt1><a:srgbClr val="FFFFFF"/></a:lt1>
      <a:dk2><a:srgbClr val="2F3437"/></a:dk2><a:lt2><a:srgbClr val="F7F6F2"/></a:lt2>
      <a:accent1><a:srgbClr val="3B6EA8"/></a:accent1><a:accent2><a:srgbClr val="3F8F72"/></a:accent2>
      <a:accent3><a:srgbClr val="BFA46F"/></a:accent3><a:accent4><a:srgbClr val="C45A3A"/></a:accent4>
      <a:accent5><a:srgbClr val="687078"/></a:accent5><a:accent6><a:srgbClr val="D8D3C8"/></a:accent6>
      <a:hlink><a:srgbClr val="3B6EA8"/></a:hlink><a:folHlink><a:srgbClr val="8D7447"/></a:folHlink>
    </a:clrScheme>
    <a:fontScheme name="BOGP Fonts">
      <a:majorFont><a:latin typeface="Yu Gothic"/><a:ea typeface="Yu Gothic"/></a:majorFont>
      <a:minorFont><a:latin typeface="Yu Gothic"/><a:ea typeface="Yu Gothic"/></a:minorFont>
    </a:fontScheme>
    <a:fmtScheme name="BOGP Format"><a:fillStyleLst/><a:lnStyleLst/><a:effectStyleLst/><a:bgFillStyleLst/></a:fmtScheme>
  </a:themeElements>
</a:theme>"""


def app_xml(nslides: int) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
            xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>Codex</Application><PresentationFormat>Widescreen</PresentationFormat>
  <Slides>{nslides}</Slides><Notes>0</Notes><HiddenSlides>0</HiddenSlides>
  <MMClips>0</MMClips><ScaleCrop>false</ScaleCrop>
  <Company>master_BOGP</Company><LinksUpToDate>false</LinksUpToDate>
  <SharedDoc>false</SharedDoc><HyperlinksChanged>false</HyperlinksChanged><AppVersion>16.0000</AppVersion>
</Properties>"""


def core_xml() -> str:
    now = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
                   xmlns:dc="http://purl.org/dc/elements/1.1/"
                   xmlns:dcterms="http://purl.org/dc/terms/"
                   xmlns:dcmitype="http://purl.org/dc/dcmitype/"
                   xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>BOGP 12min Presentation</dc:title>
  <dc:creator>Codex</dc:creator>
  <cp:lastModifiedBy>Codex</cp:lastModifiedBy>
  <dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified>
</cp:coreProperties>"""


def misc_xml(name: str) -> str:
    if name == "presProps":
        return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:presentationPr xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"/>"""
    if name == "viewProps":
        return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:viewPr xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"/>"""
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><a:tblStyleLst xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" def="{5C22544A-7EE6-4342-B048-85BDC9FD1C3A}"/>"""


def build() -> Path:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    slides = [factory() for factory in SLIDE_BUILDERS]
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        n = len(slides)
        z.writestr("[Content_Types].xml", content_types(n))
        z.writestr("_rels/.rels", package_rels())
        z.writestr("docProps/app.xml", app_xml(n))
        z.writestr("docProps/core.xml", core_xml())
        z.writestr("ppt/presentation.xml", presentation_xml(n))
        z.writestr("ppt/_rels/presentation.xml.rels", presentation_rels(n))
        z.writestr("ppt/presProps.xml", misc_xml("presProps"))
        z.writestr("ppt/viewProps.xml", misc_xml("viewProps"))
        z.writestr("ppt/tableStyles.xml", misc_xml("tableStyles"))
        z.writestr("ppt/theme/theme1.xml", theme_xml())
        z.writestr("ppt/slideMasters/slideMaster1.xml", master_xml())
        z.writestr("ppt/slideMasters/_rels/slideMaster1.xml.rels", master_rels())
        z.writestr("ppt/slideLayouts/slideLayout1.xml", layout_xml())
        z.writestr("ppt/slideLayouts/_rels/slideLayout1.xml.rels", layout_rels())
        for i, slide in enumerate(slides, start=1):
            z.writestr(f"ppt/slides/slide{i}.xml", slide.xml())
            z.writestr(f"ppt/slides/_rels/slide{i}.xml.rels", slide.rels_xml())
            for media_name, source in slide.media:
                z.write(source, f"ppt/media/{media_name}")
    return OUT


if __name__ == "__main__":
    built = build()
    print(f"created {built}")
    print(f"size {built.stat().st_size:,} bytes")
