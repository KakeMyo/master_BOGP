#!/usr/bin/env python3
"""Build the dense discussion deck with MO-GP and expanded BO intro slides."""

from __future__ import annotations

from pathlib import Path
import zipfile

from build_bogp_12min_presentation import (
    COLORS,
    OUT as _BASE_OUT,
    SlideBuilder,
    app_xml,
    content_types,
    core_xml,
    layout_rels,
    layout_xml,
    master_rels,
    master_xml,
    misc_xml,
    package_rels,
    presentation_rels,
    presentation_xml,
    theme_xml,
)
from build_bogp_12min_presentation_dense import (
    algorithm_archive_slide,
    background_slide,
    future_slide,
    method_architecture_slide,
    multiobjective_slide,
    problem_slide,
    setup_slide,
    state_action_reward_slide,
    title_slide,
)
from build_bogp_12min_presentation_dense_discussion import (
    discussion_slide,
    final_results_slide,
    k_behavior_slide,
    note_card,
    pareto_slide,
    trajectory_stability_slide,
)


ROOT = Path(__file__).resolve().parents[1]
OUT = _BASE_OUT.with_name("BOGP_12min_presentation_dense_intro_gp_bo_expanded_discussion.pptx")


def multiobjective_gp_intro_slide() -> SlideBuilder:
    s = SlideBuilder(2, "多目的GPとは", "BACKGROUND")
    s.header()
    s.text(0.85, 1.42, 7.0, 0.38, "GPは，木構造の数式・プログラムを進化的に探索する方法", 18, COLORS["ink"], bold=True)
    s.card(0.85, 2.05, 3.3, 1.2, "個体 T", "数式やプログラムを\n木構造として表す", COLORS["blue"], COLORS["blue_light"])
    s.card(4.85, 2.05, 3.3, 1.2, "進化操作", "選択・交叉・突然変異で\n候補式を更新する", COLORS["orange"], COLORS["orange_light"])
    s.card(8.85, 2.05, 3.3, 1.2, "多目的化", "1つの最良解ではなく\n解集合を得る", COLORS["green"], COLORS["green_light"])
    s.line(4.23, 2.65, 0.48, 0, COLORS["gray_mid"], width=14000, arrow=True)
    s.line(8.23, 2.65, 0.48, 0, COLORS["gray_mid"], width=14000, arrow=True)

    s.rect(1.35, 4.0, 0.9, 0.36, fill=COLORS["dark"], line=None)
    s.text(1.35, 4.05, 0.9, 0.14, "+", 14, COLORS["white"], bold=True, align="c")
    for x, label in [(0.95, "x1"), (2.1, "sin"), (3.0, "x2")]:
        s.rect(x, 4.72, 0.72, 0.34, fill=COLORS["blue_light"], line=COLORS["blue"])
        s.text(x, 4.77, 0.72, 0.14, label, 10, COLORS["blue"], bold=True, align="c")
    s.line(1.8, 4.36, -0.45, 0.35, COLORS["gray_mid"], width=8000)
    s.line(1.8, 4.36, 0.65, 0.35, COLORS["gray_mid"], width=8000)
    s.line(2.46, 5.06, 0.42, 0.24, COLORS["gray_mid"], width=8000)
    s.text(0.9, 5.45, 3.3, 0.25, "木構造個体の例", 12, COLORS["muted"], align="c")

    s.text(
        4.7,
        4.0,
        3.8,
        0.82,
        "minimize  f(T) = ( f1(T), f2(T) )",
        19,
        COLORS["dark"],
        bold=True,
        align="c",
        valign="m",
        fill=COLORS["gray_light"],
        radius=True,
    )
    s.text(4.8, 5.02, 3.6, 0.5, "本研究では\nf1: 予測誤差,  f2: 式木サイズ", 13, COLORS["ink"], align="c")

    s.line(9.1, 5.85, 2.6, 0, COLORS["ink"], width=9000, arrow=True)
    s.line(9.1, 5.85, 0, -2.0, COLORS["ink"], width=9000, arrow=True)
    for x, y in [(9.35, 5.35), (9.75, 4.9), (10.28, 4.45), (10.9, 4.1), (11.55, 3.86)]:
        s.rect(x, y, 0.12, 0.12, fill=COLORS["green"], line=None)
    s.line(9.4, 5.4, 2.25, -1.55, COLORS["green"], width=8000)
    s.text(9.7, 3.55, 2.3, 0.28, "Pareto front", 12, COLORS["green"], bold=True, align="c")

    s.text(1.0, 6.35, 11.1, 0.35, "多目的GPの目標は，精度と複雑さのトレードオフを表すPareto frontを改善すること．", 14, COLORS["dark"], bold=True, align="c")
    return s


def objective_novelty_bo_slide() -> SlideBuilder:
    s = SlideBuilder(5, "研究目的と提案法の要点", "INTRODUCTION")
    s.header()
    s.text(
        0.95,
        1.42,
        11.25,
        0.82,
        "目的: 交叉率・突然変異率を探索状態に応じて動的に調整し，\n多目的GPの収束性と多様性を改善する",
        22,
        COLORS["dark"],
        bold=True,
        align="c",
        valign="m",
        fill=COLORS["gray_light"],
        radius=True,
    )
    s.card(0.95, 2.8, 3.45, 1.25, "BOとは", "探索状態に応じて\n次に試す制御入力を選ぶ\n外側の最適化器", COLORS["gold_dark"], "EFE7D4")
    s.card(4.85, 2.8, 3.45, 1.25, "制御入力", "pc: 交叉率\npm: 突然変異率\nk: 更新周期", COLORS["blue"], COLORS["blue_light"])
    s.card(8.75, 2.8, 3.45, 1.25, "提案の本質", "固定率の置き換えではなく\n状態依存の閉ループ制御", COLORS["green"], COLORS["green_light"])
    s.text(1.05, 4.65, 11.1, 0.55, "GPをプラント，BOを制御器として，観測 → 制御 → 実行 → 評価を繰り返す．", 18, COLORS["dark"], bold=True, align="c")
    s.text(1.15, 5.72, 10.9, 0.4, "BOの中身は次スライドで，surrogate・不確実性・獲得関数の3点に分けて説明する．", 14, COLORS["muted"], align="c")
    return s


def bayesian_optimization_intro_slide() -> SlideBuilder:
    s = SlideBuilder(6, "BOとは", "METHOD")
    s.header()
    s.text(0.85, 1.42, 8.0, 0.38, "評価に時間がかかるブラックボックス関数を，少ない試行で効率よく最適化する方法", 18, COLORS["ink"], bold=True)

    s.card(0.85, 2.08, 3.25, 1.15, "1. Surrogate", "観測済みデータから\n未知の報酬関数を近似する", COLORS["blue"], COLORS["blue_light"])
    s.card(4.45, 2.08, 3.25, 1.15, "2. Uncertainty", "まだ試していない候補の\n不確実性も推定する", COLORS["gold_dark"], "EFE7D4")
    s.card(8.05, 2.08, 3.25, 1.15, "3. Acquisition", "予測値と不確実性から\n次の候補を選ぶ", COLORS["green"], COLORS["green_light"])
    s.line(4.18, 2.65, 0.2, 0, COLORS["gray_mid"], width=12000, arrow=True)
    s.line(7.78, 2.65, 0.2, 0, COLORS["gray_mid"], width=12000, arrow=True)

    s.text(
        1.0,
        3.85,
        5.1,
        0.62,
        "Dℓ = { (x_i, u_i, r_i) }",
        22,
        COLORS["dark"],
        bold=True,
        align="c",
        valign="m",
        fill=COLORS["gray_light"],
        radius=True,
    )
    s.text(
        6.65,
        3.85,
        5.1,
        0.62,
        "u_next = argmax EI(u | xℓ)",
        21,
        COLORS["dark"],
        bold=True,
        align="c",
        valign="m",
        fill=COLORS["gray_light"],
        radius=True,
    )
    s.line(6.15, 4.16, 0.35, 0, COLORS["gray_mid"], width=14000, arrow=True)

    note_card(
        s,
        0.95,
        5.18,
        3.5,
        1.05,
        "本研究の候補 u",
        "u = (pc, pm, k)\n操作率と更新周期を同時に選ぶ",
        COLORS["blue"],
        COLORS["blue_light"],
        body_size=10,
    )
    note_card(
        s,
        4.9,
        5.18,
        3.5,
        1.05,
        "本研究の観測値 r",
        "HV改善・多様性維持・制御コストから作る報酬",
        COLORS["green"],
        COLORS["green_light"],
        body_size=10,
    )
    note_card(
        s,
        8.85,
        5.18,
        3.5,
        1.05,
        "本研究の文脈 x",
        "現在のGP探索状態\nHV, 多様性, 停滞長など",
        COLORS["gold_dark"],
        "EFE7D4",
        body_size=10,
    )
    return s


def bo_controller_detail_slide() -> SlideBuilder:
    s = SlideBuilder(9, "BO制御器の処理", "METHOD")
    s.header()
    s.text(0.85, 1.42, 7.4, 0.38, "一般的なBOを，本研究では状態付きの制御入力選択に使う", 18, COLORS["ink"], bold=True)
    s.card(0.85, 2.0, 3.4, 1.35, "文脈を固定", "更新時点の状態 xℓ を観測し\nその状態に条件づける", COLORS["blue"], COLORS["blue_light"])
    s.card(4.85, 2.0, 3.4, 1.35, "kごとに評価", "kを離散候補として列挙し\nEI_k(xℓ,pc,pm) を比較", COLORS["gold_dark"], "EFE7D4")
    s.card(8.85, 2.0, 3.4, 1.35, "行動を決定", "最大EIの候補を\n次の uℓ=(pc,pm,k) とする", COLORS["green"], COLORS["green_light"])
    s.text(
        1.0,
        4.05,
        11.1,
        0.72,
        "uℓ* = argmax  EI_k( xℓ, pc, pm )",
        25,
        COLORS["dark"],
        bold=True,
        align="c",
        valign="m",
        fill=COLORS["gray_light"],
        radius=True,
    )
    s.text(1.0, 5.28, 11.1, 0.45, "非文脈BOとの違い: r=f(pc,pm,k) ではなく，探索状態を含む r=f(x,pc,pm,k) を学習する．", 15, COLORS["dark"], bold=True, align="c")
    s.text(1.15, 6.02, 10.9, 0.35, "つまり，BOは単に良い固定率を探すのではなく，状態ごとに操作強度と更新周期を切り替える．", 13, COLORS["muted"], align="c")
    return s


SLIDE_BUILDERS = [
    title_slide,
    multiobjective_gp_intro_slide,
    background_slide,
    multiobjective_slide,
    objective_novelty_bo_slide,
    bayesian_optimization_intro_slide,
    method_architecture_slide,
    state_action_reward_slide,
    bo_controller_detail_slide,
    algorithm_archive_slide,
    problem_slide,
    setup_slide,
    final_results_slide,
    trajectory_stability_slide,
    pareto_slide,
    k_behavior_slide,
    discussion_slide,
    future_slide,
]


def renumber_slide(slide: SlideBuilder, new_number: int) -> SlideBuilder:
    old_number = getattr(slide, "number", new_number)
    old_token = f">{old_number:02d}<"
    new_token = f">{new_number:02d}<"
    slide.parts = [part.replace(old_token, new_token) for part in slide.parts]
    slide.number = new_number
    return slide


def build() -> Path:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    slides = [renumber_slide(factory(), i) for i, factory in enumerate(SLIDE_BUILDERS, start=1)]
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
    print(f"slides {len(SLIDE_BUILDERS)}")
    print(f"size {built.stat().st_size:,} bytes")
