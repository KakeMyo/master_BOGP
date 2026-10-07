#!/usr/bin/env python3
"""Build a denser 12-minute BOGP presentation deck.

The previous deck keeps one message per slide.  This version intentionally
packs a little more information into each slide, reducing the deck to 16 slides
while preserving readability for a 12-minute research progress talk.
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


ROOT = Path(__file__).resolve().parents[1]
OUT = _BASE_OUT.with_name("BOGP_12min_presentation_dense.pptx")


def title_slide() -> SlideBuilder:
    s = SlideBuilder(1, None)
    s.rect(0.48, 0.44, 12.38, 6.55, fill=COLORS["dark"], line=None, radius=False)
    s.rect(0.82, 0.76, 11.7, 5.95, fill="474D4F", line=None, radius=False, alpha=68000)
    s.rect(9.05, 0.95, 3.2, 2.75, fill=COLORS["gold"], line=None, alpha=15000)
    s.rect(0.95, 5.0, 2.8, 1.65, fill=COLORS["blue"], line=None, alpha=13000)
    s.text(1.0, 0.98, 4.3, 0.32, "12 min progress talk / dense version", 10, COLORS["gold"], bold=True)
    s.text(
        1.15,
        2.05,
        11.0,
        1.55,
        "多目的GPにおける\n操作率の閉ループ制御",
        37,
        COLORS["white"],
        bold=True,
        align="c",
        valign="m",
        margin=0,
    )
    s.text(
        1.65,
        3.82,
        10.0,
        0.55,
        "文脈付きBOで 交叉率・突然変異率・更新周期 を動的に調整する",
        16,
        "F2EFE6",
        bold=True,
        align="c",
    )
    s.line(3.0, 4.62, 7.3, 0, color=COLORS["gold"], width=13000)
    s.text(1.3, 5.55, 10.9, 0.4, "Friedman-II シンボリック回帰による初期本実験", 13, "F2EFE6", align="c")
    s.text(1.3, 6.18, 10.9, 0.32, "Myojin / master_BOGP", 10, "D7D0BE", align="c")
    return s


def background_slide() -> SlideBuilder:
    s = SlideBuilder(2, "背景と課題: 固定率GPの限界", "BACKGROUND")
    s.header()
    s.text(0.85, 1.45, 5.4, 0.42, "操作率は探索の性格を決めるが，固定値では段階変化に追従しにくい", 19, COLORS["ink"], bold=True)
    s.card(0.85, 2.05, 3.05, 1.25, "交叉率 pc", "有望な部分構造を\n組み替える強度", COLORS["blue"], COLORS["blue_light"])
    s.card(4.15, 2.05, 3.05, 1.25, "突然変異率 pm", "新しい構造を導入し\n局所解を避ける強度", COLORS["orange"], COLORS["orange_light"])
    s.card(7.45, 2.05, 4.7, 1.25, "固定率の懸念", "探索初期・中盤・終盤で望ましい操作が変わるが，固定率は状態を見ない", COLORS["gold_dark"], "EFE7D4")
    s.line(1.35, 4.25, 10.7, 0, COLORS["gray_mid"], width=12000)
    for x, label, want in [
        (1.5, "探索初期", "広く試す\n多様性を確保"),
        (5.45, "中盤", "有望領域へ\n絞り込み"),
        (9.55, "終盤", "微調整\n早期収束回避"),
    ]:
        s.rect(x - 0.08, 4.17, 0.16, 0.16, fill=COLORS["gold"], line=None)
        s.text(x - 0.8, 4.55, 1.6, 0.32, label, 14, COLORS["gold_dark"], bold=True, align="c")
        s.text(x - 0.9, 4.95, 1.8, 0.65, want, 14, COLORS["ink"], align="c")
    s.text(1.0, 6.12, 11.0, 0.5, "論点: 操作率を静的ハイパーパラメータではなく，探索状態に応じて更新する制御入力として扱う", 17, COLORS["dark"], bold=True, align="c", fill=COLORS["gray_light"], radius=True)
    return s


def multiobjective_slide() -> SlideBuilder:
    s = SlideBuilder(3, "多目的GPで見るべきもの", "BACKGROUND")
    s.header()
    s.text(0.85, 1.45, 5.2, 0.42, "多目的GPでは，単一の最良式ではなくトレードオフ解集合を得る", 19, COLORS["ink"], bold=True)
    s.line(1.2, 5.95, 4.5, 0, COLORS["ink"], width=12000, arrow=True)
    s.line(1.2, 5.95, 0, -3.75, COLORS["ink"], width=12000, arrow=True)
    s.text(3.15, 6.16, 2.0, 0.25, "式木サイズ", 12, COLORS["muted"], align="c")
    s.text(0.25, 3.35, 1.1, 0.25, "誤差", 12, COLORS["muted"], align="c")
    for x, y in [(1.55, 5.05), (2.0, 4.35), (2.65, 3.65), (3.55, 3.05), (4.8, 2.52)]:
        s.rect(x, y, 0.13, 0.13, fill=COLORS["blue"], line=None)
    s.line(1.62, 5.1, 3.3, -2.55, COLORS["blue"], width=9500)
    s.text(2.85, 2.18, 2.8, 0.3, "Pareto front", 14, COLORS["blue"], bold=True)
    s.card(6.45, 1.9, 5.45, 1.1, "評価軸1: 収束性", "HVやパレートフロント位置が良い領域へ進むか", COLORS["green"], COLORS["green_light"])
    s.card(6.45, 3.35, 5.45, 1.1, "評価軸2: 多様性", "異なる構造・複雑さの解候補を維持できるか", COLORS["gold_dark"], "EFE7D4")
    s.card(6.45, 4.8, 5.45, 1.1, "評価軸3: 複雑さ", "高精度だが巨大な式だけに偏っていないか", COLORS["orange"], COLORS["orange_light"])
    return s


def objective_novelty_slide() -> SlideBuilder:
    s = SlideBuilder(4, "研究目的と提案法の要点", "INTRODUCTION")
    s.header()
    s.text(0.95, 1.48, 11.25, 0.9, "目的: 交叉率・突然変異率を探索状態に応じて動的に調整し，\n多目的GPの収束性と多様性を改善する", 24, COLORS["dark"], bold=True, align="c", valign="m", fill=COLORS["gray_light"], radius=True)
    s.card(0.95, 3.0, 3.55, 1.45, "要点1", "GPをプラント，BOを制御器とする閉ループで設計", COLORS["blue"], COLORS["blue_light"])
    s.card(4.85, 3.0, 3.55, 1.45, "要点2", "pc, pm だけでなく k も制御し，再調整周期を変える", COLORS["green"], COLORS["green_light"])
    s.card(8.75, 3.0, 3.55, 1.45, "要点3", "状態 x を条件に含める文脈付きBOとして扱う", COLORS["gold_dark"], "EFE7D4")
    s.text(1.1, 5.45, 11.1, 0.5, "固定率の置き換えではなく，「操作強度」と「更新周期」の状態依存制御が本質", 19, COLORS["dark"], bold=True, align="c")
    return s


def method_architecture_slide() -> SlideBuilder:
    s = SlideBuilder(5, "提案手法: 閉ループ制御の全体像", "METHOD")
    s.header()
    s.card(0.85, 2.35, 2.7, 1.25, "State Observation", "τ, HV, ΔHV, D\nLbar, s", COLORS["blue"], COLORS["blue_light"])
    s.card(4.15, 2.35, 2.7, 1.25, "Contextual BO", "f(x,pc,pm,k)\nEIで次行動を選択", COLORS["gold_dark"], "EFE7D4")
    s.card(7.45, 2.35, 2.7, 1.25, "Action", "uℓ=(pc,pm,k)\n区間中は保持", COLORS["orange"], COLORS["orange_light"])
    s.card(10.2, 2.35, 2.35, 1.25, "GP Plant", "k世代進化\n統計を返す", COLORS["green"], COLORS["green_light"])
    for x in [3.62, 6.92, 10.02]:
        s.line(x, 2.98, 0.45, 0, COLORS["gray_mid"], width=14000, arrow=True)
    s.line(10.95, 3.92, 0, 1.05, COLORS["gray_mid"], width=12000)
    s.line(10.95, 4.97, -9.0, 0, COLORS["gray_mid"], width=12000)
    s.line(1.95, 4.97, 0, -0.95, COLORS["gray_mid"], width=12000, arrow=True)
    s.text(3.1, 4.53, 7.6, 0.36, "区間統計: ΔHV rate, Dbar, Ck  →  報酬 rℓ  →  学習データ (xℓ,uℓ,rℓ)", 14, COLORS["muted"], align="c")
    s.text(1.0, 6.08, 11.0, 0.5, "GPの世代進化を観測し，BOが次の操作率と更新周期を決め直す", 18, COLORS["dark"], bold=True, align="c", fill=COLORS["gray_light"], radius=True)
    return s


def state_action_reward_slide() -> SlideBuilder:
    s = SlideBuilder(6, "状態・行動・報酬の定義", "METHOD")
    s.header()
    s.text(0.85, 1.45, 6.4, 0.38, "BOに入る情報と，BOが返す制御入力を明確に分ける", 18, COLORS["ink"], bold=True)
    s.card(0.85, 2.0, 3.85, 2.0, "状態 xℓ", "τ: 世代進行率\nHV: 現在の解集合品質\nΔHV: 直近改善量\nD: 多様性\nLbar: 平均木サイズ\ns: 停滞長", COLORS["blue"], COLORS["blue_light"])
    s.card(4.95, 2.0, 3.15, 2.0, "行動 uℓ", "pc: 交叉率\npm: 突然変異率\nk: 次回更新までの世代数\n\n制約: pc+pm≤1", COLORS["orange"], COLORS["orange_light"])
    s.card(8.35, 2.0, 3.9, 2.0, "報酬 rℓ", "主項: ΔHV rate\n副項: 区間平均多様性 Dbar\n抑制項: 制御コスト Ck\n\n進捗と多様性の両立を評価", COLORS["green"], COLORS["green_light"])
    s.text(1.0, 4.75, 11.2, 0.6, "rℓ = wp·ΔHVrate + wd·SD(Dbar) − wc·Ck(k)", 22, COLORS["dark"], bold=True, align="c", fill=COLORS["gray_light"], radius=True)
    s.text(1.15, 5.95, 10.8, 0.45, "k導入時の不公平を避けるため，区間総改善量ではなく世代あたり改善量を主項にする．", 14, COLORS["muted"], align="c")
    return s


def bo_detail_slide() -> SlideBuilder:
    s = SlideBuilder(7, "BO制御器の処理", "METHOD")
    s.header()
    s.text(0.85, 1.45, 6.0, 0.38, "kを離散候補として列挙し，pc, pm, k を同時に選ぶ", 18, COLORS["ink"], bold=True)
    s.card(0.85, 2.05, 3.55, 1.45, "Surrogate", "kごとにGP回帰器を持つ\nfk(x,pc,pm) ~ GP", COLORS["blue"], COLORS["blue_light"])
    s.card(4.65, 2.05, 3.55, 1.45, "Acquisition", "現在状態 xℓ を固定し\nEIk(xℓ,pc,pm) を比較", COLORS["gold_dark"], "EFE7D4")
    s.card(8.45, 2.05, 3.55, 1.45, "Decision", "全k候補と操作率候補から\n最大EIの行動を採用", COLORS["green"], COLORS["green_light"])
    s.text(1.0, 4.25, 11.0, 0.65, "uℓ* = argmax k∈K(xℓ), pc,pm∈U  EI_k(xℓ,pc,pm)", 22, COLORS["dark"], bold=True, align="c", fill=COLORS["gray_light"], radius=True)
    s.text(1.05, 5.65, 10.9, 0.52, "非文脈BOとの差: r=f(pc,pm,k) ではなく，探索状態を含む r=f(x,pc,pm,k) を学習する．", 16, COLORS["dark"], bold=True, align="c")
    return s


def algorithm_archive_slide() -> SlideBuilder:
    s = SlideBuilder(8, "アルゴリズムとアーカイブ", "METHOD")
    s.header()
    steps = [
        "1. 初期集団を生成し，warm-up設計点で複数区間を評価",
        "2. 更新時点で状態 xℓ を観測",
        "3. BOが uℓ=(pc,pm,k) を選択",
        "4. GPを k 世代実行し，区間統計を取得",
        "5. 報酬 rℓ を計算し，(xℓ,uℓ,rℓ) を履歴に追加",
    ]
    for i, text in enumerate(steps):
        y = 1.55 + i * 0.7
        s.rect(0.9, y, 7.0, 0.52, fill="F4F1EA", line=COLORS["line"])
        s.text(1.08, y + 0.09, 6.65, 0.25, text, 12, COLORS["ink"], bold=True)
    s.card(8.35, 1.65, 3.85, 1.5, "アーカイブ", "探索中に得られた非劣解を保存する外部集合．\n最終Pareto frontとHV評価に用いる．", COLORS["blue"], COLORS["blue_light"])
    s.card(8.35, 3.55, 3.85, 1.5, "現在集団", "多様性や平均木サイズなど，探索状態の観測に用いる．", COLORS["green"], COLORS["green_light"])
    s.text(1.0, 6.08, 11.0, 0.45, "成果評価はアーカイブ，状態観測は現在集団を中心に分担する．", 17, COLORS["dark"], bold=True, align="c", fill=COLORS["gray_light"], radius=True)
    return s


def problem_slide() -> SlideBuilder:
    s = SlideBuilder(9, "対象問題: Friedman-II シンボリック回帰", "EXPERIMENT")
    s.header()
    s.text(0.85, 1.45, 5.4, 0.38, "真の関数が既知で，非線形構造を含む初期本実験向け問題", 18, COLORS["ink"], bold=True)
    eq = "y = 10 sin(πx1x2) + 20(x3 − 0.5)^2 + 10x4 + 5x5"
    s.text(0.95, 2.05, 11.25, 0.75, eq, 21, COLORS["dark"], bold=True, align="c", valign="m", fill=COLORS["gray_light"], radius=True)
    s.card(0.95, 3.25, 3.65, 1.35, "問題の特徴", "相互作用，三角関数，二次項，線形項を含む", COLORS["blue"], COLORS["blue_light"])
    s.card(4.9, 3.25, 3.65, 1.35, "目的関数", "f1: 訓練NRMSE\nf2: 式木サイズ", COLORS["green"], COLORS["green_light"])
    s.card(8.85, 3.25, 3.65, 1.35, "評価の位置づけ", "真の式の完全復元ではなく\n精度--複雑さの解集合を評価", COLORS["gold_dark"], "EFE7D4")
    s.text(1.0, 5.65, 11.0, 0.42, "GPには真の式構造を与えず，入出力サンプルから任意の式木を探索させる．", 15, COLORS["muted"], align="c")
    return s


def setup_slide() -> SlideBuilder:
    s = SlideBuilder(10, "実験設定と比較条件", "EXPERIMENT")
    s.header()
    s.text(0.85, 1.42, 6.0, 0.36, "提案法を複数の固定率GPと同一評価回数で比較する", 18, COLORS["ink"], bold=True)
    widths = [2.65, 3.35, 4.3]
    headers = ["方法", "設定", "目的"]
    x0, y0 = 0.85, 1.95
    for j, h in enumerate(headers):
        s.rect(x0 + sum(widths[:j]), y0, widths[j], 0.43, fill=COLORS["dark"], line=COLORS["dark"], radius=False)
        s.text(x0 + sum(widths[:j]), y0 + 0.07, widths[j], 0.2, h, 11, COLORS["white"], bold=True, align="c")
    rows = [
        ("BO current", "pc,pm,kをBO制御", "提案法"),
        ("標準固定率", "pc=0.7, pm=0.2", "通常GPの基準"),
        ("高突然変異", "pmを高める", "多様性重視の固定率"),
        ("高交叉", "pcを高める", "組み替え重視の固定率"),
    ]
    for i, row in enumerate(rows):
        y = y0 + 0.48 + i * 0.52
        for j, cell in enumerate(row):
            s.rect(x0 + sum(widths[:j]), y, widths[j], 0.48, fill=("F4F1EA" if i % 2 == 0 else COLORS["white"]), line=COLORS["line"], radius=False)
            s.text(x0 + sum(widths[:j]) + 0.05, y + 0.08, widths[j] - 0.1, 0.2, cell, 10, COLORS["ink"], bold=(j == 0), align="c")
    s.card(0.95, 5.15, 2.75, 1.15, "seed", "100 seed", COLORS["blue"], COLORS["blue_light"])
    s.card(3.95, 5.15, 2.75, 1.15, "世代数", "warm-up 18\n+ 評価 60", COLORS["green"], COLORS["green_light"])
    s.card(6.95, 5.15, 2.75, 1.15, "評価回数", "1872 evaluations", COLORS["gold_dark"], "EFE7D4")
    s.card(9.95, 5.15, 2.25, 1.15, "archive key", "topology + value", COLORS["orange"], COLORS["orange_light"])
    return s


def final_results_slide() -> SlideBuilder:
    s = SlideBuilder(11, "結果1: 最終HV・多様性", "RESULTS")
    s.header()
    s.image(FINAL_HV_FIG, 0.75, 1.45, 7.55, 3.95)
    s.card(8.6, 1.55, 3.75, 1.0, "BO current", "HV 0.802 ± 0.022\nDiversity 0.641 ± 0.087", COLORS["blue"], COLORS["blue_light"])
    s.card(8.6, 2.9, 3.75, 1.0, "標準固定率", "HV 0.783 ± 0.055\nDiversity 0.624 ± 0.109", COLORS["gold_dark"], "EFE7D4")
    s.card(8.6, 4.25, 3.75, 1.0, "高突然変異", "HV 0.808 ± 0.030\n現時点の最良平均", COLORS["orange"], COLORS["orange_light"])
    s.text(0.95, 6.05, 11.2, 0.46, "提案法は標準固定率を上回り，seed間のHVばらつきは最小だった．一方，高突然変異固定率を平均HVで上回るには改善が必要．", 15, COLORS["dark"], bold=True, align="c", fill=COLORS["gray_light"], radius=True)
    return s


def trajectory_stability_slide() -> SlideBuilder:
    s = SlideBuilder(12, "結果2: 世代推移と安定性", "RESULTS")
    s.header()
    s.image(HV_PROGRESS_FIG, 0.75, 1.45, 7.8, 4.25)
    s.text(8.85, 1.55, 3.6, 0.45, "HV標準偏差", 18, COLORS["ink"], bold=True, align="c")
    for i, (name, val, c, f) in enumerate([
        ("BO current", "0.022", COLORS["blue"], COLORS["blue_light"]),
        ("高突然変異", "0.030", COLORS["orange"], COLORS["orange_light"]),
        ("高交叉", "0.030", COLORS["green"], COLORS["green_light"]),
        ("標準固定率", "0.055", COLORS["gold_dark"], "EFE7D4"),
    ]):
        y = 2.15 + i * 0.77
        s.rect(8.85, y, 3.55, 0.58, fill=f, line=c)
        s.text(9.02, y + 0.08, 1.75, 0.22, name, 10, c, bold=True)
        s.text(11.0, y + 0.05, 1.05, 0.28, val, 16, COLORS["dark"], bold=True, align="r")
    s.text(1.0, 6.12, 11.0, 0.42, "提案法は評価後半で標準固定率より高いHV水準を維持し，結果の安定化にも寄与した可能性がある．", 15, COLORS["dark"], bold=True, align="c")
    return s


def pareto_slide() -> SlideBuilder:
    s = SlideBuilder(13, "結果3: Pareto front形状", "RESULTS")
    s.header()
    s.image(PARETO_FIG, 0.7, 1.42, 7.25, 5.45)
    s.card(8.25, 1.58, 3.8, 1.25, "なぜ形を見るか", "HVだけでは，どの複雑さ領域が改善されたか分からない", COLORS["blue"], COLORS["blue_light"])
    s.card(8.25, 3.08, 3.8, 1.25, "見る領域", "低複雑度・高精度・中間解のどこに解が分布するか", COLORS["green"], COLORS["green_light"])
    s.card(8.25, 4.58, 3.8, 1.25, "今後の評価", "領域別HVや代表式の構造分析で補助的に確認する", COLORS["gold_dark"], "EFE7D4")
    return s


def k_behavior_slide() -> SlideBuilder:
    s = SlideBuilder(14, "結果4: 更新周期 k の挙動", "RESULTS")
    s.header()
    s.image(K_ALIGNMENT_FIG, 0.72, 1.35, 7.1, 5.0)
    s.text(8.05, 1.48, 4.0, 0.72, "代表seedで k の時間的な意味を見る", 21, COLORS["dark"], bold=True, align="c")
    s.card(8.15, 2.72, 3.75, 1.05, "読み方", "kは選択後の区間に保持される制御入力", COLORS["blue"], COLORS["blue_light"])
    s.card(8.15, 4.08, 3.75, 1.05, "見る対応", "HV上昇・停滞・多様性低下とk切替", COLORS["orange"], COLORS["orange_light"])
    s.text(8.1, 5.58, 3.85, 0.52, "登場回数だけでなく，どの状態で選ばれたかを議論する．", 13, COLORS["muted"], align="c")
    return s


def discussion_slide() -> SlideBuilder:
    s = SlideBuilder(15, "総合考察", "DISCUSSION")
    s.header()
    s.card(0.85, 1.65, 3.75, 1.75, "分かったこと", "提案法は標準固定率よりHV・多様性で良く，ばらつきも小さい．\n閉ループ制御の有効性の兆しがある．", COLORS["green"], COLORS["green_light"])
    s.card(4.9, 1.65, 3.75, 1.75, "まだ言えないこと", "高突然変異固定率を一貫して上回っていない．\nBO制御器の設計が十分とは言い切れない．", COLORS["orange"], COLORS["orange_light"])
    s.card(8.95, 1.65, 3.75, 1.75, "重要な論点", "提案法の強みは可変率そのものではなく，状態依存で切り替える点にある．", COLORS["blue"], COLORS["blue_light"])
    s.text(1.0, 4.5, 11.2, 0.78, "結論: 現行法は標準固定率GPに対する改善を示した．\n次は，状態依存制御・k制御・多様性報酬の寄与を分離して検証する必要がある．", 21, COLORS["dark"], bold=True, align="c", valign="m", fill=COLORS["gray_light"], radius=True)
    return s


def future_slide() -> SlideBuilder:
    s = SlideBuilder(16, "今後やること", "DISCUSSION")
    s.header()
    items = [
        ("1. BO制御器の改善", "報酬スケーリング，多様性項の重み，EI比較，warm-up設計を見直す．", COLORS["blue"], COLORS["blue_light"]),
        ("2. 比較実験の追加", "非文脈BO，固定k版，多様性項なし版で寄与を切り分ける．", COLORS["green"], COLORS["green_light"]),
        ("3. 評価指標の拡張", "領域別Pareto評価，安定性，制御回数，計算コストも見る．", COLORS["gold_dark"], "EFE7D4"),
        ("4. 対象問題の拡張", "他のSRベンチマークや構造探索問題で有効条件を確認する．", COLORS["orange"], COLORS["orange_light"]),
    ]
    for i, (title, body, c, f) in enumerate(items):
        x = 0.95 + (i % 2) * 6.1
        y = 1.65 + (i // 2) * 1.68
        s.card(x, y, 5.25, 1.22, title, body, c, f)
    s.text(1.15, 5.25, 10.9, 0.78, "発表で伝える最終メッセージ:\nGPの操作率設定は，固定値探索ではなく状態依存の閉ループ制御問題として扱える．", 22, COLORS["dark"], bold=True, align="c", valign="m", fill=COLORS["gray_light"], radius=True)
    s.text(1.1, 6.65, 11.1, 0.3, "次の実験では「どの設計要素が効いているか」を明確にする．", 13, COLORS["muted"], align="c")
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
