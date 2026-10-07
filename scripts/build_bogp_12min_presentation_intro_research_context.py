#!/usr/bin/env python3
"""Build the presentation with an introduction aligned to the resume opening."""

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
    note_card,
    pareto_slide,
    trajectory_stability_slide,
)
from build_bogp_12min_presentation_dense_intro_gp_bo_expanded_discussion import (
    bayesian_optimization_intro_slide,
    bo_controller_detail_slide,
)


ROOT = Path(__file__).resolve().parents[1]
OUT = _BASE_OUT.with_name("BOGP_12min_presentation_intro_research_context.pptx")


def operator_dependency_slide() -> SlideBuilder:
    s = SlideBuilder(2, "背景: GPの操作率は探索を左右する", "BACKGROUND")
    s.header()
    s.text(0.85, 1.42, 7.1, 0.38, "GPは木構造を進化させるため，交叉・突然変異が探索挙動に直接効く", 18, COLORS["ink"], bold=True)

    s.card(0.9, 2.02, 3.1, 1.2, "交叉率 pc", "有望な部分構造を\n組み替える強度", COLORS["blue"], COLORS["blue_light"])
    s.card(4.35, 2.02, 3.1, 1.2, "突然変異率 pm", "新しい構造を導入し\n局所解を避ける強度", COLORS["orange"], COLORS["orange_light"])
    s.card(7.8, 2.02, 4.25, 1.2, "設定の難しさ", "問題ごと・探索段階ごとに\n望ましい値が変わる", COLORS["gold_dark"], "EFE7D4")

    s.text(1.0, 3.7, 2.8, 0.35, "操作率", 18, COLORS["dark"], bold=True, align="c")
    s.line(2.4, 4.0, 2.1, 0.85, COLORS["gray_mid"], width=12000, arrow=True)
    s.line(2.4, 4.0, 4.2, 0.85, COLORS["gray_mid"], width=12000, arrow=True)
    s.line(2.4, 4.0, 6.25, 0.85, COLORS["gray_mid"], width=12000, arrow=True)
    for x, label, c, f in [
        (4.1, "多様性", COLORS["green"], COLORS["green_light"]),
        (6.2, "収束速度", COLORS["blue"], COLORS["blue_light"]),
        (8.3, "解集合品質", COLORS["orange"], COLORS["orange_light"]),
    ]:
        s.rect(x, 4.75, 1.65, 0.72, fill=f, line=c)
        s.text(x + 0.05, 4.95, 1.55, 0.2, label, 13, c, bold=True, align="c")

    s.text(0.95, 5.95, 11.2, 0.42, "固定率は基準として扱いやすいが，実行中の探索状態には反応できない．", 16, COLORS["dark"], bold=True, align="c", fill=COLORS["gray_light"], radius=True)
    s.text(9.95, 6.78, 2.35, 0.2, "[R1][R2]", 8, COLORS["muted"], align="r")
    return s


def related_work_operator_control_slide() -> SlideBuilder:
    s = SlideBuilder(3, "関連研究: 操作率を固定しない方向性", "BACKGROUND")
    s.header()
    s.text(0.85, 1.42, 7.4, 0.38, "先行研究は，操作率を探索過程の制御入力として扱う重要性を示している", 18, COLORS["ink"], bold=True)

    s.card(0.9, 2.0, 3.35, 1.45, "パラメータ制御", "実行前に値を決める調整ではなく\n探索中の情報で値を変える", COLORS["blue"], COLORS["blue_light"])
    s.card(4.9, 2.0, 3.35, 1.45, "GPでの適応操作率", "演算子確率や木構造の複雑さに応じて\n操作率を変える研究がある", COLORS["green"], COLORS["green_light"])
    s.card(8.9, 2.0, 3.35, 1.45, "残る論点", "多目的GPで pc, pm, k を\n状態依存に同時制御したい", COLORS["orange"], COLORS["orange_light"])
    for x in [4.35, 8.35]:
        s.line(x, 2.72, 0.38, 0, COLORS["gray_mid"], width=14000, arrow=True)

    s.text(
        1.0,
        4.35,
        11.1,
        0.82,
        "関連研究からの示唆:\n操作率は単なる定数ではなく，探索状態に応じて変えるべき制御対象になり得る．",
        21,
        COLORS["dark"],
        bold=True,
        align="c",
        valign="m",
        fill=COLORS["gray_light"],
        radius=True,
    )
    s.text(1.0, 5.82, 11.1, 0.35, "本研究では，この方向性を多目的GPの閉ループ制御へ拡張する．", 15, COLORS["muted"], align="c")
    s.text(9.45, 6.78, 2.85, 0.2, "[R1][R2][R3][R4][R5]", 8, COLORS["muted"], align="r")
    return s


def multiobjective_challenge_slide() -> SlideBuilder:
    s = SlideBuilder(4, "多目的GPでは何が難しいか", "BACKGROUND")
    s.header()
    s.text(0.85, 1.42, 7.4, 0.38, "多目的GPでは，単一の最良個体ではなくトレードオフ解集合が目的になる", 18, COLORS["ink"], bold=True)

    s.line(1.15, 5.75, 4.55, 0, COLORS["ink"], width=12000, arrow=True)
    s.line(1.15, 5.75, 0, -3.55, COLORS["ink"], width=12000, arrow=True)
    s.text(3.1, 5.98, 2.0, 0.25, "式木サイズ", 12, COLORS["muted"], align="c")
    s.text(0.25, 3.25, 1.1, 0.25, "誤差", 12, COLORS["muted"], align="c")
    for x, y in [(1.55, 4.95), (2.0, 4.25), (2.7, 3.55), (3.65, 2.95), (4.75, 2.52)]:
        s.rect(x, y, 0.13, 0.13, fill=COLORS["blue"], line=None)
    s.line(1.62, 5.0, 3.25, -2.45, COLORS["blue"], width=9000)
    s.text(2.75, 2.15, 2.8, 0.3, "Pareto front", 14, COLORS["blue"], bold=True)

    s.card(6.35, 1.8, 5.55, 1.1, "収束性", "誤差が小さい領域へ進めるか", COLORS["green"], COLORS["green_light"])
    s.card(6.35, 3.25, 5.55, 1.1, "多様性", "異なる複雑さ・構造の解を維持できるか", COLORS["gold_dark"], "EFE7D4")
    s.card(6.35, 4.7, 5.55, 1.1, "解集合評価", "HVだけでなく front 形状や集団状態も見る", COLORS["orange"], COLORS["orange_light"])
    s.text(9.8, 6.78, 2.5, 0.2, "[R6][R7]", 8, COLORS["muted"], align="r")
    return s


def research_gap_objective_slide() -> SlideBuilder:
    s = SlideBuilder(5, "研究ギャップと目的", "INTRODUCTION")
    s.header()
    s.text(0.85, 1.42, 7.0, 0.38, "関連研究を踏まえ，本研究では操作率設定を閉ループ制御問題として捉える", 18, COLORS["ink"], bold=True)

    s.card(0.9, 2.02, 3.45, 1.35, "ギャップ", "固定値探索では\n世代進行・停滞・多様性低下に\n応じた切り替えが難しい", COLORS["orange"], COLORS["orange_light"])
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
    s.text(1.1, 5.65, 11.0, 0.45, "ここで k は次回更新までの世代数であり，「いつ再調整するか」も制御対象に含める．", 15, COLORS["muted"], align="c")
    return s


SLIDE_BUILDERS = [
    title_slide,
    operator_dependency_slide,
    related_work_operator_control_slide,
    multiobjective_challenge_slide,
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
