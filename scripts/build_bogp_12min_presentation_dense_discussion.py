#!/usr/bin/env python3
"""Build the dense BOGP deck with resume-derived result discussion.

This keeps the previous dense deck intact and creates a new PPTX where result
slides include short interpretation boxes based on the seminar resume and the
current Friedman-II main experiment summary.
"""

from __future__ import annotations

from pathlib import Path
import zipfile

from build_bogp_12min_presentation import (
    COLORS,
    FINAL_HV_FIG,
    HV_PROGRESS_FIG,
    K_ALIGNMENT_FIG,
    OUT as _BASE_OUT,
    PARETO_FIG,
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
    bo_detail_slide,
    future_slide,
    method_architecture_slide,
    multiobjective_slide,
    objective_novelty_slide,
    problem_slide,
    setup_slide,
    state_action_reward_slide,
    title_slide,
)


ROOT = Path(__file__).resolve().parents[1]
OUT = _BASE_OUT.with_name("BOGP_12min_presentation_dense_discussion.pptx")


def note_card(
    s: SlideBuilder,
    x: float,
    y: float,
    w: float,
    h: float,
    label: str,
    body: str,
    color: str,
    fill: str,
    body_size: int = 11,
) -> None:
    s.rect(x, y, w, h, fill=fill, line=color)
    s.text(x + 0.12, y + 0.1, w - 0.24, 0.24, label, 11, color, bold=True)
    s.text(x + 0.12, y + 0.42, w - 0.24, h - 0.52, body, body_size, COLORS["ink"])


def final_results_slide() -> SlideBuilder:
    s = SlideBuilder(11, "結果1: 最終HV・多様性", "RESULTS")
    s.header()
    s.image(FINAL_HV_FIG, 0.72, 1.43, 7.35, 3.72)
    s.card(8.32, 1.42, 3.85, 0.88, "BO current", "HV 0.802 ± 0.022 / D 0.641 ± 0.087", COLORS["blue"], COLORS["blue_light"])
    s.card(8.32, 2.48, 3.85, 0.88, "標準固定率", "HV 0.783 ± 0.055 / D 0.624 ± 0.109", COLORS["gold_dark"], "EFE7D4")
    s.card(8.32, 3.54, 3.85, 0.88, "高突然変異", "HV 0.808 ± 0.030 / D 0.646 ± 0.082", COLORS["orange"], COLORS["orange_light"])
    note_card(
        s,
        0.85,
        5.45,
        5.45,
        1.03,
        "読み取り",
        "提案法は標準固定率GPより最終HV・多様性が高く，HVのばらつきも小さい．",
        COLORS["green"],
        COLORS["green_light"],
    )
    note_card(
        s,
        6.65,
        5.45,
        5.55,
        1.03,
        "考察",
        "ただし高突然変異固定率が平均HVで最良であり，全baselineに勝ったとは主張しない．",
        COLORS["orange"],
        COLORS["orange_light"],
    )
    return s


def trajectory_stability_slide() -> SlideBuilder:
    s = SlideBuilder(12, "結果2: 世代推移と安定性", "RESULTS")
    s.header()
    s.image(HV_PROGRESS_FIG, 0.72, 1.42, 7.55, 4.0)
    s.text(8.55, 1.45, 3.75, 0.3, "最終HVの標準偏差", 15, COLORS["ink"], bold=True, align="c")
    for i, (name, val, c, f) in enumerate(
        [
            ("BO current", "0.022", COLORS["blue"], COLORS["blue_light"]),
            ("高突然変異", "0.030", COLORS["orange"], COLORS["orange_light"]),
            ("高交叉", "0.030", COLORS["green"], COLORS["green_light"]),
            ("標準固定率", "0.055", COLORS["gold_dark"], "EFE7D4"),
        ]
    ):
        y = 1.93 + i * 0.58
        s.rect(8.55, y, 3.75, 0.45, fill=f, line=c)
        s.text(8.72, y + 0.07, 1.85, 0.18, name, 9, c, bold=True)
        s.text(11.0, y + 0.04, 1.0, 0.22, val, 13, COLORS["dark"], bold=True, align="r")
    note_card(
        s,
        8.55,
        4.55,
        3.75,
        0.95,
        "読み取り",
        "評価後半で標準固定率より高いHV水準を維持した．",
        COLORS["blue"],
        COLORS["blue_light"],
        body_size=10,
    )
    note_card(
        s,
        0.95,
        5.82,
        11.15,
        0.67,
        "考察",
        "閉ループ制御が乱数seedによる不安定さを抑えた可能性がある．ただし要因は非文脈BO・固定k版・多様性項なし版との比較で切り分ける必要がある．",
        COLORS["green"],
        COLORS["green_light"],
        body_size=12,
    )
    return s


def pareto_slide() -> SlideBuilder:
    s = SlideBuilder(13, "結果3: Pareto front形状", "RESULTS")
    s.header()
    s.image(PARETO_FIG, 0.68, 1.42, 7.1, 5.25)
    note_card(
        s,
        8.05,
        1.52,
        4.1,
        1.1,
        "読み取り",
        "HVは解集合を1値に要約するが，低複雑度・高精度・中間領域の差は見えにくい．",
        COLORS["blue"],
        COLORS["blue_light"],
    )
    note_card(
        s,
        8.05,
        2.95,
        4.1,
        1.1,
        "考察",
        "標準固定率との差は，単一の高精度個体ではなく複数領域でfrontを押し広げた可能性として見る．",
        COLORS["green"],
        COLORS["green_light"],
    )
    note_card(
        s,
        8.05,
        4.38,
        4.1,
        1.1,
        "今後の分析",
        "領域別HVや代表式の構造確認で，どの領域が改善されたかを補助的に評価する．",
        COLORS["gold_dark"],
        "EFE7D4",
    )
    return s


def k_behavior_slide() -> SlideBuilder:
    s = SlideBuilder(14, "結果4: 更新周期 k の挙動", "RESULTS")
    s.header()
    s.image(K_ALIGNMENT_FIG, 0.68, 1.35, 6.95, 4.95)
    s.text(7.82, 1.42, 4.35, 0.48, "代表seedで k の世代対応を確認", 19, COLORS["dark"], bold=True, align="c")
    s.card(7.95, 2.12, 4.05, 0.9, "図の読み方", "kは選択後の区間に保持される", COLORS["blue"], COLORS["blue_light"])
    s.card(7.95, 3.18, 4.05, 0.9, "見るべき対応", "HV上昇・停滞・多様性低下とk切替", COLORS["green"], COLORS["green_light"])
    note_card(
        s,
        7.95,
        4.45,
        4.05,
        0.95,
        "考察",
        "登場回数だけではなく，どの状態で短周期・長周期が選ばれたかを議論する．",
        COLORS["orange"],
        COLORS["orange_light"],
        body_size=10,
    )
    s.text(0.95, 6.32, 11.05, 0.28, "kは単なる効率化変数ではなく，状態に応じて制御周期を切り替える入力として扱う．", 13, COLORS["muted"], align="c")
    return s


def discussion_slide() -> SlideBuilder:
    s = SlideBuilder(15, "総合考察", "DISCUSSION")
    s.header()
    s.card(0.85, 1.55, 2.85, 1.55, "1. 枠組みは動いた", "状態を観測し pc, pm, k を切り替える閉ループ制御として実行できた．", COLORS["blue"], COLORS["blue_light"])
    s.card(3.95, 1.55, 2.85, 1.55, "2. 標準固定率には有効", "標準固定率GPより最終HV・多様性が高く，安定性も良い傾向がある．", COLORS["green"], COLORS["green_light"])
    s.card(7.05, 1.55, 2.85, 1.55, "3. 強いbaselineに課題", "高突然変異固定率には平均HVで届かず，BO制御器に改善余地が残る．", COLORS["orange"], COLORS["orange_light"])
    s.card(10.15, 1.55, 2.25, 1.55, "4. 次の切り分け", "非文脈BO\n固定k版\n多様性項なし", COLORS["gold_dark"], "EFE7D4")
    s.text(
        1.0,
        4.25,
        11.15,
        0.9,
        "今回の位置づけ: 「全baselineに勝った」ではなく，\n標準固定率GPに対する有効性の兆しと，改善すべき制御器設計が明確になった．",
        22,
        COLORS["dark"],
        bold=True,
        align="c",
        valign="m",
        fill=COLORS["gray_light"],
        radius=True,
    )
    s.text(1.15, 5.85, 10.9, 0.42, "したがって次段階では，状態依存制御・k制御・多様性報酬の寄与を分離して検証する．", 15, COLORS["muted"], align="c")
    return s


SLIDE_BUILDERS = [
    title_slide,
    background_slide,
    multiobjective_slide,
    objective_novelty_slide,
    method_architecture_slide,
    state_action_reward_slide,
    bo_detail_slide,
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
    print(f"slides {len(SLIDE_BUILDERS)}")
    print(f"size {built.stat().st_size:,} bytes")
