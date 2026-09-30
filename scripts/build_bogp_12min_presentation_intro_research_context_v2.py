#!/usr/bin/env python3
"""Build the intro-context deck v2 with the user-specified opening flow."""

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
    future_slide,
    method_architecture_slide,
    problem_slide,
    setup_slide,
    state_action_reward_slide,
    title_slide,
)
from build_bogp_12min_presentation_dense_discussion import (
    discussion_slide,
    final_results_slide,
    k_behavior_slide,
    pareto_slide,
    trajectory_stability_slide,
)
from build_bogp_12min_presentation_dense_intro_gp_bo_expanded_discussion import (
    bayesian_optimization_intro_slide,
    bo_controller_detail_slide,
)


ROOT = Path(__file__).resolve().parents[1]
OUT = _BASE_OUT.with_name("BOGP_12min_presentation_intro_research_context_v2.pptx")


def gp_and_operator_background_slide() -> SlideBuilder:
    s = SlideBuilder(2, "背景: GPと操作率", "BACKGROUND")
    s.header()
    s.text(0.85, 1.42, 7.9, 0.38, "回帰や構造探索などで用いられるGPは，数式・プログラムを進化的に探索する手法である", 18, COLORS["ink"], bold=True)

    s.card(0.85, 2.03, 3.55, 1.42, "GPとは", "回帰・構造探索などに用いられる\n数式やプログラムを木構造として表し\n進化的に探索する手法", COLORS["blue"], COLORS["blue_light"])
    s.card(4.85, 2.03, 3.25, 1.42, "探索を左右する操作率", "交叉率 pc: 構造の組み替え\n突然変異率 pm: 新規構造の導入", COLORS["orange"], COLORS["orange_light"])
    s.card(8.55, 2.03, 3.65, 1.42, "調整の難しさ", "適切な値は問題ごとに異なり\n経験や試行錯誤が必要になる", COLORS["gold_dark"], "EFE7D4")

    s.rect(1.2, 4.12, 0.82, 0.32, fill=COLORS["dark"], line=None)
    s.text(1.2, 4.16, 0.82, 0.12, "+", 13, COLORS["white"], bold=True, align="c")
    for x, label in [(0.95, "x1"), (1.95, "sin"), (2.9, "x2")]:
        s.rect(x, 4.86, 0.66, 0.32, fill=COLORS["blue_light"], line=COLORS["blue"])
        s.text(x, 4.9, 0.66, 0.12, label, 9, COLORS["blue"], bold=True, align="c")
    s.line(1.61, 4.44, -0.32, 0.38, COLORS["gray_mid"], width=8000)
    s.line(1.61, 4.44, 0.68, 0.38, COLORS["gray_mid"], width=8000)
    s.line(2.31, 5.18, 0.42, 0.28, COLORS["gray_mid"], width=8000)
    s.text(0.95, 5.55, 2.85, 0.2, "木構造として表現", 11, COLORS["muted"], align="c")

    s.text(4.6, 4.1, 1.5, 0.42, "pc", 27, COLORS["blue"], bold=True, align="c")
    s.text(4.3, 4.62, 2.1, 0.35, "交叉率", 14, COLORS["blue"], bold=True, align="c")
    s.text(6.85, 4.1, 1.5, 0.42, "pm", 27, COLORS["orange"], bold=True, align="c")
    s.text(6.55, 4.62, 2.1, 0.35, "突然変異率", 14, COLORS["orange"], bold=True, align="c")
    s.line(6.1, 4.32, 0.55, 0, COLORS["gray_mid"], width=11000, arrow=True)

    s.text(0.95, 6.15, 11.2, 0.43, "さらに，適切なパラメータは問題だけでなく探索段階にも依存する．", 17, COLORS["dark"], bold=True, align="c", fill=COLORS["gray_light"], radius=True)
    s.text(9.95, 6.78, 2.35, 0.2, "[R1][R2][R3]", 8, COLORS["muted"], align="r")
    return s


def related_work_operator_control_slide() -> SlideBuilder:
    s = SlideBuilder(3, "関連研究: 操作率を固定しない方向性", "BACKGROUND")
    s.header()
    s.text(0.85, 1.42, 8.4, 0.38, "先行研究は，GPの操作率が探索過程を制御する重要な入力であることを示している", 18, COLORS["ink"], bold=True)

    s.card(0.9, 2.03, 3.45, 1.42, "演算子出現率の適応", "GP実行中に遺伝的演算子の\n適用確率を調整する例がある", COLORS["blue"], COLORS["blue_light"])
    s.card(4.85, 2.03, 3.45, 1.42, "木構造に応じた調整", "木構造の複雑さに応じて\n交叉率・突然変異率を調整する例がある", COLORS["green"], COLORS["green_light"])
    s.card(8.8, 2.03, 3.45, 1.42, "示唆", "操作率は単なる実装上の定数ではなく\n探索過程を制御する入力である", COLORS["orange"], COLORS["orange_light"])
    for x in [4.38, 8.33]:
        s.line(x, 2.74, 0.33, 0, COLORS["gray_mid"], width=13000, arrow=True)

    s.text(
        1.05,
        4.25,
        11.05,
        0.82,
        "関連研究からの流れ:\n固定した操作率を使うだけでなく，探索状態に応じて操作率を変える方向性が有効になり得る．",
        21,
        COLORS["dark"],
        bold=True,
        align="c",
        valign="m",
        fill=COLORS["gray_light"],
        radius=True,
    )
    s.text(1.15, 5.78, 10.95, 0.36, "本研究では，この考え方を多目的GPに拡張し，pc, pm に加えて更新周期 k も制御対象に含める．", 14, COLORS["muted"], align="c")
    s.text(9.95, 6.78, 2.35, 0.2, "[R1][R2]", 8, COLORS["muted"], align="r")
    return s


def multiobjective_gp_need_slide() -> SlideBuilder:
    s = SlideBuilder(4, "多目的GPにおいて", "BACKGROUND")
    s.header()
    s.text(0.85, 1.42, 8.0, 0.38, "多目的GPでは，単一の最良個体ではなくPareto front近似を得ることが目的になる", 18, COLORS["ink"], bold=True)

    s.line(1.15, 5.75, 4.55, 0, COLORS["ink"], width=12000, arrow=True)
    s.line(1.15, 5.75, 0, -3.55, COLORS["ink"], width=12000, arrow=True)
    s.text(3.05, 5.98, 2.0, 0.25, "複雑さ", 12, COLORS["muted"], align="c")
    s.text(0.25, 3.25, 1.1, 0.25, "誤差", 12, COLORS["muted"], align="c")
    for x, y in [(1.55, 4.95), (2.0, 4.25), (2.7, 3.55), (3.65, 2.95), (4.75, 2.52)]:
        s.rect(x, y, 0.13, 0.13, fill=COLORS["blue"], line=None)
    s.line(1.62, 5.0, 3.25, -2.45, COLORS["blue"], width=9000)
    s.text(2.75, 2.15, 2.8, 0.3, "Pareto front", 14, COLORS["blue"], bold=True)

    s.card(6.35, 1.75, 5.55, 1.05, "目的", "精度と複雑さなどのトレードオフを表す\nPareto front近似を得る", COLORS["blue"], COLORS["blue_light"])
    s.card(6.35, 3.1, 5.55, 1.05, "課題", "単に収束を速めるだけでなく\n多様な解候補を維持する必要がある", COLORS["gold_dark"], "EFE7D4")
    s.card(6.35, 4.45, 5.55, 1.05, "方策", "探索状態に応じた交叉率・突然変異率の動的調整は\n収束性と多様性の両立に有効な方策になり得る", COLORS["green"], COLORS["green_light"])

    s.text(1.0, 6.32, 11.1, 0.3, "つまり，多目的GPでは「速く良い解へ進むこと」と「解集合の広がりを保つこと」を同時に考える必要がある．", 13, COLORS["muted"], align="c")
    return s


def research_gap_objective_slide() -> SlideBuilder:
    s = SlideBuilder(5, "研究ギャップと目的", "INTRODUCTION")
    s.header()
    s.text(0.85, 1.42, 8.2, 0.38, "したがって本研究では，操作率設定を状態観測に基づく閉ループ制御問題として扱う", 18, COLORS["ink"], bold=True)

    s.card(0.9, 2.02, 3.45, 1.35, "ギャップ", "固定値探索では\n問題・探索段階の変化に応じた\n切り替えが難しい", COLORS["orange"], COLORS["orange_light"])
    s.card(4.75, 2.02, 3.45, 1.35, "目的", "交叉率・突然変異率を\n探索状態に応じて動的調整し\n収束性と多様性を改善する", COLORS["green"], COLORS["green_light"])
    s.card(8.6, 2.02, 3.45, 1.35, "BOの役割", "探索状態に応じて\n次に試す制御入力を選ぶ\n外側の最適化器", COLORS["blue"], COLORS["blue_light"])

    s.text(
        1.1,
        4.25,
        11.0,
        0.78,
        "提案法:  uℓ = ( pc, pm, k )  を文脈付きBOで逐次決定する",
        24,
        COLORS["dark"],
        bold=True,
        align="c",
        valign="m",
        fill=COLORS["gray_light"],
        radius=True,
    )
    s.text(1.1, 5.65, 11.0, 0.45, "GPをプラント，BOを制御器とみなし，操作率だけでなく「いつ再調整するか」も制御する．", 15, COLORS["muted"], align="c")
    return s


SLIDE_BUILDERS = [
    title_slide,
    gp_and_operator_background_slide,
    related_work_operator_control_slide,
    multiobjective_gp_need_slide,
    research_gap_objective_slide,
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
