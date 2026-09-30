#!/usr/bin/env python3
"""Build a Japanese 12-minute story deck for the BOGP seminar talk.

The deck is intentionally concise: 12 main slides plus 6 backup slides.
It reuses the existing editable PresentationML helper used by earlier decks in
this repository, but keeps this version as a new file so previous decks remain
unchanged.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

from build_bogp_12min_presentation import (
    COLORS,
    FIG_DIR,
    FINAL_HV_FIG,
    HV_PROGRESS_FIG,
    K_ALIGNMENT_FIG,
    PARETO_FIG,
    ROOT,
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


OUT = ROOT / "slides" / "BOGP_12min_presentation_story_jp_v1.pptx"
K_COUNTS_FIG = FIG_DIR / "main_k_selection_counts.png"


def claim(s: SlideBuilder, text: str, y: float = 1.38, color: str = COLORS["dark"]) -> None:
    s.text(
        0.78,
        y,
        11.8,
        0.58,
        text,
        18,
        color,
        bold=True,
        align="c",
        valign="m",
        fill=COLORS["gray_light"],
        radius=True,
    )


def table(
    s: SlideBuilder,
    x: float,
    y: float,
    widths: list[float],
    header: list[str],
    rows: list[list[str]],
    row_h: float = 0.52,
    font_size: int = 11,
) -> None:
    for j, h in enumerate(header):
        xj = x + sum(widths[:j])
        s.rect(xj, y, widths[j], row_h, fill=COLORS["dark"], line=COLORS["dark"], radius=False)
        s.text(xj + 0.03, y + 0.08, widths[j] - 0.06, 0.24, h, font_size, COLORS["white"], bold=True, align="c")
    for i, row in enumerate(rows):
        yy = y + row_h + i * row_h
        for j, cell in enumerate(row):
            xj = x + sum(widths[:j])
            fill = "F4F1EA" if i % 2 == 0 else COLORS["white"]
            s.rect(xj, yy, widths[j], row_h, fill=fill, line=COLORS["line"], radius=False)
            s.text(
                xj + 0.04,
                yy + 0.08,
                widths[j] - 0.08,
                0.24,
                cell,
                font_size,
                COLORS["ink"],
                bold=j == 0,
                align="c",
            )


def tiny_tag(s: SlideBuilder, x: float, y: float, text: str, color: str) -> None:
    s.text(x, y, 1.65, 0.3, text, 10, COLORS["white"], bold=True, align="c", fill=color, radius=True)


def slide_01_title() -> SlideBuilder:
    s = SlideBuilder(1, None)
    s.rect(0.55, 0.48, 12.25, 6.45, fill=COLORS["dark"], line=None, radius=False)
    s.rect(0.85, 0.78, 11.65, 5.86, fill="41484A", line=None, radius=False, alpha=72000)
    s.rect(9.05, 0.82, 3.1, 3.1, fill=COLORS["gold"], line=None, radius=True, alpha=17000)
    s.rect(0.95, 4.82, 2.35, 2.35, fill=COLORS["blue"], line=None, radius=True, alpha=12000)
    s.text(0.95, 0.92, 4.0, 0.3, "12分発表 / 日本語版 v1", 10, COLORS["gold"], bold=True)
    s.text(
        1.1,
        2.0,
        11.1,
        1.4,
        "多目的GPにおける\n操作率の状態依存制御",
        34,
        COLORS["white"],
        bold=True,
        align="c",
        valign="m",
        margin=0,
    )
    s.text(
        1.5,
        3.72,
        10.3,
        0.55,
        "文脈付きBOで交叉率・突然変異率・更新周期を動的に調整する",
        16,
        "F2EFE6",
        align="c",
        valign="m",
        margin=0,
    )
    s.line(3.2, 4.55, 6.95, 0, color=COLORS["gold"], width=14000)
    s.text(1.1, 5.72, 11.1, 0.38, "Friedman-II シンボリック回帰による初期本実験", 12, "D7D0BE", align="c")
    return s


def slide_02_mogp_goal() -> SlideBuilder:
    s = SlideBuilder(2, "背景: 多目的GPでは何を目指すのか", "BACKGROUND")
    s.header()
    claim(s, "目的は1つの最良解ではなく，精度と複雑さのパレートフロントを得ること")
    s.line(1.05, 6.1, 4.8, 0, COLORS["ink"], width=12000, arrow=True)
    s.line(1.05, 6.1, 0, -3.85, COLORS["ink"], width=12000, arrow=True)
    s.text(2.92, 6.33, 2.2, 0.3, "式の複雑さ", 12, COLORS["muted"], align="c")
    s.text(0.28, 3.25, 1.3, 0.3, "誤差", 12, COLORS["muted"], align="c")
    points = [(1.52, 5.0), (2.06, 4.34), (2.82, 3.64), (3.92, 3.1), (5.0, 2.74)]
    for x, y in points:
        s.rect(x, y, 0.13, 0.13, fill=COLORS["blue"], line=None)
    s.line(1.58, 5.05, 3.52, -2.35, COLORS["blue"], width=9500)
    s.text(3.35, 2.35, 2.4, 0.34, "Pareto front", 14, COLORS["blue"], bold=True)
    s.card(7.1, 2.35, 4.75, 1.2, "収束性", "誤差の小さい解へ近づく", COLORS["green"], COLORS["green_light"])
    s.card(7.1, 3.95, 4.75, 1.2, "多様性", "異なる複雑さ・構造の解を残す", COLORS["gold_dark"], "EFE7D4")
    s.text(7.25, 5.65, 4.45, 0.5, "両立が難しいため，探索制御が重要", 16, COLORS["dark"], bold=True, align="c")
    return s


def slide_03_fixed_problem() -> SlideBuilder:
    s = SlideBuilder(3, "課題: 固定率では探索状態に対応しにくい", "BACKGROUND")
    s.header()
    claim(s, "探索初期・中盤・停滞時で望ましい交叉率・突然変異率は異なる")
    phases = [
        ("探索初期", "広く試す\n突然変異を強めたい", COLORS["orange"], COLORS["orange_light"]),
        ("中盤", "有望構造を組み替える\n交叉が効きやすい", COLORS["blue"], COLORS["blue_light"]),
        ("停滞時", "局所解から脱出する\n再探索が必要", COLORS["green"], COLORS["green_light"]),
    ]
    for i, (title, body, c, f) in enumerate(phases):
        x = 1.0 + i * 4.05
        s.card(x, 2.72, 3.25, 1.75, title, body, c, f)
        if i < 2:
            s.line(x + 3.35, 3.58, 0.55, 0, COLORS["gray_mid"], width=15000, arrow=True)
    s.text(
        1.35,
        5.6,
        10.65,
        0.62,
        "固定率GPは「今の探索状態」を見ないため，段階に応じた切り替えができない．",
        19,
        COLORS["dark"],
        bold=True,
        align="c",
        fill=COLORS["gray_light"],
        radius=True,
    )
    return s


def slide_04_related_gap() -> SlideBuilder:
    s = SlideBuilder(4, "先行研究と残る課題", "POSITION")
    s.header()
    claim(s, "差分は，多目的GPの世代状態を条件に pc, pm, k を同時制御する点")
    header = ["方法", "状態観測", "pc, pm", "k", "本研究との差分"]
    rows = [
        ["固定率GP", "なし", "固定", "固定", "探索状態に適応しない"],
        ["手設計スケジュール", "なし", "時間で変更", "固定", "状態ではなく世代番号で決める"],
        ["非文脈BO", "なし", "BOで選択", "選択可", "現在状態を条件にしない"],
        ["提案法", "あり", "状態依存", "状態依存", "操作強度と更新周期を同時制御"],
    ]
    table(s, 0.68, 2.35, [2.35, 1.55, 1.65, 1.15, 5.65], header, rows, row_h=0.62, font_size=10)
    s.text(1.1, 6.25, 11.0, 0.42, "新規性の中心は「BOを使うこと」ではなく「状態条件付きの閉ループ制御」にある．", 16, COLORS["dark"], bold=True, align="c")
    return s


def slide_05_objective_novelty() -> SlideBuilder:
    s = SlideBuilder(5, "研究目的と新規性", "POSITION")
    s.header()
    s.text(
        0.85,
        1.45,
        11.65,
        1.1,
        "目的: 交叉率・突然変異率を探索状態に応じて動的調整し，\n多目的GPの収束性と多様性を改善する",
        24,
        COLORS["dark"],
        bold=True,
        align="c",
        valign="m",
    )
    cards = [
        ("閉ループ化", "GPをプラント，BOを制御器として扱う", COLORS["blue"], COLORS["blue_light"]),
        ("状態依存", "HV，多様性，停滞長などを文脈として使う", COLORS["green"], COLORS["green_light"]),
        ("同時制御", "pc, pm だけでなく更新周期 k も決める", COLORS["gold_dark"], "EFE7D4"),
    ]
    for i, (title, body, c, f) in enumerate(cards):
        s.card(1.0 + i * 4.05, 3.45, 3.25, 1.65, title, body, c, f)
    s.text(1.2, 6.08, 10.9, 0.45, "固定ハイパーパラメータ調整ではなく，状態依存の制御問題として定義する．", 17, COLORS["dark"], bold=True, align="c")
    return s


def slide_06_closed_loop() -> SlideBuilder:
    s = SlideBuilder(6, "提案手法: 閉ループ制御として見る", "METHOD")
    s.header()
    claim(s, "観測 → 行動決定 → GP進化 → 報酬計算 → BO更新 を繰り返す")
    boxes = [
        ("状態観測", "τ, HV, ΔHV\nD, Lbar, s", 0.75, 3.15, COLORS["green"], COLORS["green_light"]),
        ("文脈付きBO", "状態 x を条件に\nEIを比較", 3.55, 3.15, COLORS["blue"], COLORS["blue_light"]),
        ("行動出力", "pc, pm, k", 6.35, 3.15, COLORS["gold_dark"], "EFE7D4"),
        ("GP Plant", "k世代だけ進化", 9.15, 3.15, COLORS["orange"], COLORS["orange_light"]),
    ]
    for title, body, x, y, c, f in boxes:
        s.card(x, y, 2.25, 1.35, title, body, c, f)
    for x in [3.12, 5.92, 8.72]:
        s.line(x, 3.84, 0.36, 0, COLORS["gray_mid"], width=14000, arrow=True)
    s.line(10.25, 4.62, -8.35, 1.2, COLORS["gray_mid"], width=11000, arrow=True)
    s.text(3.1, 5.62, 7.2, 0.35, "区間統計: ΔHV rate, Dbar, Ck → 学習データ (x, u, r)", 14, COLORS["muted"], align="c")
    return s


def slide_07_state_action_reward() -> SlideBuilder:
    s = SlideBuilder(7, "BOに入れる情報とBOが決めるもの", "METHOD")
    s.header()
    claim(s, "BOは「良い固定率」ではなく，「現在状態に対する次の行動」を選ぶ")
    s.card(0.9, 2.45, 3.55, 2.2, "入力: 状態 x", "世代進行率 τ\n現在HV\n直近改善量 ΔHV\n多様性 D\n平均木サイズ Lbar\n停滞長 s", COLORS["green"], COLORS["green_light"])
    s.card(4.85, 2.45, 3.55, 2.2, "出力: 行動 u", "交叉率 pc\n突然変異率 pm\n更新周期 k\n\nkは次回更新までの世代数", COLORS["blue"], COLORS["blue_light"])
    s.card(8.8, 2.45, 3.55, 2.2, "観測: 報酬 r", "世代あたりHV改善\n区間平均多様性\n制御コスト\n\n性能と多様性の両立を評価", COLORS["gold_dark"], "EFE7D4")
    s.text(1.15, 5.78, 10.9, 0.45, "学習対象:  r = f(x, pc, pm, k)   /   非文脈BO:  r = f(pc, pm, k)", 17, COLORS["dark"], bold=True, align="c")
    return s


def slide_08_problem() -> SlideBuilder:
    s = SlideBuilder(8, "実験問題: Friedman-II シンボリック回帰", "EXPERIMENT")
    s.header()
    claim(s, "真の式の完全復元ではなく，精度--複雑さのパレートフロント改善を評価する")
    equation = "y = 10 sin(π x1 x2) + 20(x3 − 0.5)^2 + 10x4 + 5x5"
    s.text(0.92, 2.25, 11.5, 0.92, equation, 23, COLORS["dark"], bold=True, align="c", valign="m", fill=COLORS["gray_light"], radius=True)
    s.card(1.0, 3.85, 3.35, 1.3, "問題の特徴", "相互作用・三角関数・二次項・線形項を含む", COLORS["blue"], COLORS["blue_light"])
    s.card(4.95, 3.85, 3.35, 1.3, "2目的", "訓練NRMSEを小さく\n式木サイズを小さく", COLORS["green"], COLORS["green_light"])
    s.card(8.9, 3.85, 3.35, 1.3, "評価の考え方", "真の式はデータ生成用\nGPには構造を与えない", COLORS["gold_dark"], "EFE7D4")
    return s


def slide_09_setup() -> SlideBuilder:
    s = SlideBuilder(9, "実験設定と比較条件", "EXPERIMENT")
    s.header()
    claim(s, "同じ評価回数で，提案法と複数の固定率GPを比較する")
    header = ["条件", "設定", "位置づけ"]
    rows = [
        ["提案法", "pc, pm, k をBOで更新", "状態依存制御"],
        ["標準固定率", "pc=0.80, pm=0.05", "通常GPの基準"],
        ["高突然変異", "pc=0.70, pm=0.20", "多様性重視の強い固定率"],
        ["高交叉", "pc=0.90, pm=0.05", "組み替え重視の固定率"],
    ]
    table(s, 0.8, 2.2, [2.25, 4.35, 4.8], header, rows, row_h=0.58, font_size=11)
    s.card(1.05, 5.25, 3.15, 1.05, "試行数", "100 seed", COLORS["blue"], COLORS["blue_light"])
    s.card(5.05, 5.25, 3.15, 1.05, "世代数", "warm-up 18 + 本評価 60", COLORS["green"], COLORS["green_light"])
    s.card(9.05, 5.25, 3.15, 1.05, "評価", "最終アーカイブHV・多様性", COLORS["gold_dark"], "EFE7D4")
    return s


def slide_10_result_standard() -> SlideBuilder:
    s = SlideBuilder(10, "結果1: 標準固定率GPに対する改善", "RESULTS")
    s.header()
    claim(s, "提案法は標準固定率より最終HVと多様性が高く，HVのばらつきも小さい")
    s.image(FINAL_HV_FIG, 0.62, 2.08, 7.25, 4.55)
    s.card(8.2, 2.3, 3.85, 1.05, "最終HV平均", "提案法 0.802\n標準固定率 0.783", COLORS["blue"], COLORS["blue_light"])
    s.card(8.2, 3.75, 3.85, 1.05, "HV標準偏差", "提案法 0.022\n標準固定率 0.055", COLORS["green"], COLORS["green_light"])
    s.card(8.2, 5.2, 3.85, 1.05, "seed内比較", "標準固定率に\n70勝 2分 28敗", COLORS["gold_dark"], "EFE7D4")
    return s


def slide_11_result_limit() -> SlideBuilder:
    s = SlideBuilder(11, "結果2: まだ残る課題", "RESULTS")
    s.header()
    claim(s, "高突然変異固定率が平均HVで最良であり，現行BO制御器には改善余地がある")
    s.image(HV_PROGRESS_FIG, 0.72, 2.0, 7.15, 4.65)
    s.card(8.25, 2.18, 3.8, 1.12, "平均HV", "高突然変異 0.808\n提案法 0.802", COLORS["orange"], COLORS["orange_light"])
    s.card(8.25, 3.68, 3.8, 1.12, "解釈", "状態依存制御は有望\nただし最良固定率には未到達", COLORS["blue"], COLORS["blue_light"])
    s.card(8.25, 5.18, 3.8, 1.12, "次の焦点", "報酬設計，非文脈BO比較，固定k版で効果を切り分ける", COLORS["green"], COLORS["green_light"])
    return s


def slide_12_summary() -> SlideBuilder:
    s = SlideBuilder(12, "まとめと今後の方針", "CONCLUSION")
    s.header()
    claim(s, "固定率探索ではなく，状態依存の閉ループ制御として扱える見通しが得られた")
    items = [
        ("分かったこと", "標準固定率GPよりHV・多様性が改善し，seed間のばらつきも小さかった．", COLORS["blue"], COLORS["blue_light"]),
        ("残る課題", "高突然変異固定率には平均HVで届かず，BO制御器の調整余地がある．", COLORS["orange"], COLORS["orange_light"]),
        ("次にやること", "非文脈BO，固定k，多様性項なし，真の式の構成要素分析で効果を切り分ける．", COLORS["green"], COLORS["green_light"]),
    ]
    for i, (title, body, c, f) in enumerate(items):
        s.card(1.0 + i * 4.05, 2.55, 3.25, 2.05, title, body, c, f)
    s.text(1.2, 5.82, 10.9, 0.55, "主張: 操作率と更新周期を，探索状態に応じて同時に制御する枠組みを提案した．", 18, COLORS["dark"], bold=True, align="c")
    return s


def slide_13_backup_bo() -> SlideBuilder:
    s = SlideBuilder(13, "Backup: BOの基本", "BACKUP")
    s.header()
    claim(s, "高コストな評価を少ない試行で改善するための逐次最適化")
    s.card(1.05, 2.4, 3.2, 1.45, "代理モデル", "観測済みデータから\n未知の性能を予測", COLORS["blue"], COLORS["blue_light"])
    s.card(5.05, 2.4, 3.2, 1.45, "不確実性", "試していない領域の\n期待とばらつきを扱う", COLORS["green"], COLORS["green_light"])
    s.card(9.05, 2.4, 3.2, 1.45, "獲得関数", "EIで次に試す\n候補を選ぶ", COLORS["gold_dark"], "EFE7D4")
    s.text(1.1, 5.35, 11.0, 0.65, "本研究では，状態 x を固定した上で EI(x, pc, pm, k) を比較する．", 21, COLORS["dark"], bold=True, align="c", fill=COLORS["gray_light"], radius=True)
    return s


def slide_14_backup_archive() -> SlideBuilder:
    s = SlideBuilder(14, "Backup: アーカイブと現在集団", "BACKUP")
    s.header()
    claim(s, "HVと最終Pareto frontはアーカイブ，多様性は現在集団を主に見る")
    s.card(1.0, 2.45, 4.0, 2.0, "アーカイブ", "探索中に得られた非劣解を保存する外部集合\n最終Pareto frontとHV評価に使う", COLORS["blue"], COLORS["blue_light"])
    s.card(5.6, 2.45, 4.0, 2.0, "現在集団", "その世代で実際に進化している個体集合\n多様性・平均木サイズなど状態観測に使う", COLORS["green"], COLORS["green_light"])
    s.card(10.2, 2.45, 2.0, 2.0, "理由", "成果評価と\n探索状態を\n分ける", COLORS["gold_dark"], "EFE7D4")
    s.text(1.2, 5.55, 10.9, 0.45, "アーカイブキー: 木のトポロジー + ノード値で同一解を判定", 16, COLORS["dark"], bold=True, align="c")
    return s


def slide_15_backup_pareto() -> SlideBuilder:
    s = SlideBuilder(15, "Backup: Pareto front 詳細", "BACKUP")
    s.header()
    s.image(PARETO_FIG, 0.72, 1.55, 7.0, 5.65)
    s.card(8.05, 1.75, 4.0, 1.18, "読み方", "左下ほど誤差が小さく，式が簡潔", COLORS["blue"], COLORS["blue_light"])
    s.card(8.05, 3.25, 4.0, 1.18, "比較点", "低複雑度，中間，高精度側のどこを埋めるか", COLORS["green"], COLORS["green_light"])
    s.card(8.05, 4.75, 4.0, 1.18, "今後", "領域別にHVや解密度を分析する", COLORS["gold_dark"], "EFE7D4")
    return s


def slide_16_backup_k() -> SlideBuilder:
    s = SlideBuilder(16, "Backup: 更新周期 k の挙動", "BACKUP")
    s.header()
    s.image(K_ALIGNMENT_FIG, 0.68, 1.5, 7.35, 5.45)
    s.card(8.35, 1.78, 3.85, 1.2, "kの意味", "次回制御更新まで\n同じpc,pmを保持する世代数", COLORS["blue"], COLORS["blue_light"])
    s.card(8.35, 3.35, 3.85, 1.2, "見る点", "HV・多様性の変化と\nkの切替タイミング", COLORS["green"], COLORS["green_light"])
    s.card(8.35, 4.92, 3.85, 1.2, "補足", "kは効率化だけでなく\n適応制御の入力", COLORS["gold_dark"], "EFE7D4")
    return s


def slide_17_backup_k_counts() -> SlideBuilder:
    s = SlideBuilder(17, "Backup: k の選択回数", "BACKUP")
    s.header()
    if K_COUNTS_FIG.exists():
        s.image(K_COUNTS_FIG, 1.0, 1.55, 5.9, 4.9)
    else:
        s.text(1.0, 2.8, 5.9, 0.5, "k選択回数図が見つかりません", 16, COLORS["muted"], align="c")
    s.card(7.5, 1.85, 4.35, 1.15, "候補", "k ∈ {1, 3, 5}", COLORS["blue"], COLORS["blue_light"])
    s.card(7.5, 3.28, 4.35, 1.15, "解釈", "毎世代更新ではなく，状態に応じて更新間隔を変える", COLORS["green"], COLORS["green_light"])
    s.card(7.5, 4.72, 4.35, 1.15, "今後", "固定k版との比較で，k制御の効果を切り分ける", COLORS["gold_dark"], "EFE7D4")
    return s


def slide_18_backup_components() -> SlideBuilder:
    s = SlideBuilder(18, "Backup: 真の式の構成要素分析", "BACKUP")
    s.header()
    claim(s, "目的関数値だけでは分からない，式構造の獲得傾向を見る")
    components = [
        ("x1 x2", "変数間相互作用", COLORS["blue"], COLORS["blue_light"]),
        ("sin", "三角関数", COLORS["green"], COLORS["green_light"]),
        ("x3 の二次項", "非線形項", COLORS["gold_dark"], "EFE7D4"),
        ("x4, x5", "線形項", COLORS["orange"], COLORS["orange_light"]),
    ]
    for i, (title, body, c, f) in enumerate(components):
        x = 0.95 + i * 3.05
        s.rect(x, 2.65, 2.55, 2.0, fill=f, line=c)
        s.text(x + 0.15, 3.0, 2.25, 0.42, title, 21, c, bold=True, align="c")
        s.text(x + 0.15, 3.72, 2.25, 0.35, body, 13, COLORS["ink"], align="c")
    s.text(1.15, 5.7, 10.95, 0.55, "最終アーカイブ中の式が，これらの構成要素を含むかを後続分析で確認する．", 18, COLORS["dark"], bold=True, align="c")
    return s


SLIDE_BUILDERS = [
    slide_01_title,
    slide_02_mogp_goal,
    slide_03_fixed_problem,
    slide_04_related_gap,
    slide_05_objective_novelty,
    slide_06_closed_loop,
    slide_07_state_action_reward,
    slide_08_problem,
    slide_09_setup,
    slide_10_result_standard,
    slide_11_result_limit,
    slide_12_summary,
    slide_13_backup_bo,
    slide_14_backup_archive,
    slide_15_backup_pareto,
    slide_16_backup_k,
    slide_17_backup_k_counts,
    slide_18_backup_components,
]


def build() -> Path:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    slides = [factory() for factory in SLIDE_BUILDERS]
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        nslides = len(slides)
        z.writestr("[Content_Types].xml", content_types(nslides))
        z.writestr("_rels/.rels", package_rels())
        z.writestr("docProps/app.xml", app_xml(nslides))
        z.writestr("docProps/core.xml", core_xml())
        z.writestr("ppt/presentation.xml", presentation_xml(nslides))
        z.writestr("ppt/_rels/presentation.xml.rels", presentation_rels(nslides))
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
