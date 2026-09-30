from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/bogp_mpl_cache")

import matplotlib

matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


ROOT = Path(__file__).resolve().parents[1]


def _setup_font() -> None:
    font_candidates = [
        "/System/Library/Fonts/ヒラギノ角ゴシック W5.ttc",
        "/System/Library/Fonts/ヒラギノ角ゴシック W5.ttc",
        "/System/Library/Fonts/ヒラギノ丸ゴ ProN W4.ttc",
        "/System/Library/Fonts/ヒラギノ丸ゴ ProN W4.ttc",
    ]
    for candidate in font_candidates:
        path = Path(candidate)
        if path.exists():
            fm.fontManager.addfont(str(path))
            plt.rcParams["font.family"] = "Hiragino Sans"
            break
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["svg.fonttype"] = "none"


def _box(
    ax,
    x: float,
    y: float,
    w: float,
    h: float,
    title: str,
    body: str,
    face: str,
    edge: str,
    title_color: str = "#1D2B36",
    body_color: str = "#344955",
    title_size: float = 15.0,
    body_size: float = 10.8,
) -> None:
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.035,rounding_size=0.055",
        linewidth=2.0,
        edgecolor=edge,
        facecolor=face,
    )
    ax.add_patch(patch)
    ax.text(
        x + w / 2,
        y + h * 0.67,
        title,
        ha="center",
        va="center",
        fontsize=title_size,
        fontweight="bold",
        color=title_color,
    )
    ax.text(
        x + w / 2,
        y + h * 0.32,
        body,
        ha="center",
        va="center",
        fontsize=body_size,
        color=body_color,
        linespacing=1.35,
    )


def _arrow(
    ax,
    start: tuple[float, float],
    end: tuple[float, float],
    label: str = "",
    color: str = "#37474F",
    rad: float = 0.0,
    label_offset: tuple[float, float] = (0.0, 0.0),
    lw: float = 2.4,
) -> None:
    patch = FancyArrowPatch(
        start,
        end,
        arrowstyle="-|>",
        mutation_scale=19,
        linewidth=lw,
        color=color,
        connectionstyle=f"arc3,rad={rad}",
    )
    ax.add_patch(patch)
    if label:
        lx = (start[0] + end[0]) / 2 + label_offset[0]
        ly = (start[1] + end[1]) / 2 + label_offset[1]
        ax.text(
            lx,
            ly,
            label,
            ha="center",
            va="center",
            fontsize=10.3,
            color=color,
            bbox=dict(boxstyle="round,pad=0.23", fc="#FFFFFF", ec="none", alpha=0.92),
        )


def _elbow_arrow(
    ax,
    points: list[tuple[float, float]],
    label: str = "",
    label_xy: tuple[float, float] | None = None,
    color: str = "#37474F",
    lw: float = 2.3,
) -> None:
    if len(points) < 2:
        return
    xs = [p[0] for p in points[:-1]]
    ys = [p[1] for p in points[:-1]]
    ax.plot(xs, ys, linewidth=lw, color=color)
    ax.add_patch(
        FancyArrowPatch(
            points[-2],
            points[-1],
            arrowstyle="-|>",
            mutation_scale=19,
            linewidth=lw,
            color=color,
        )
    )
    if label and label_xy:
        ax.text(
            label_xy[0],
            label_xy[1],
            label,
            ha="center",
            va="center",
            fontsize=10.2,
            color=color,
            bbox=dict(boxstyle="round,pad=0.24", fc="#FFFFFF", ec="none", alpha=0.92),
        )


def main() -> int:
    _setup_font()
    output_dir = ROOT / "slides" / "figures"
    output_dir.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(13.333, 7.5))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 9)
    ax.axis("off")
    fig.patch.set_facecolor("#F8F6EF")
    ax.set_facecolor("#F8F6EF")

    colors = {
        "ink": "#21313C",
        "muted": "#60727C",
        "bo_face": "#FFF0D8",
        "bo_edge": "#D98C00",
        "plant_face": "#E4F3EA",
        "plant_edge": "#2E7D50",
        "state_face": "#E5F0FA",
        "state_edge": "#3176A8",
        "reward_face": "#FFF8CD",
        "reward_edge": "#B59B14",
        "data_face": "#EFEAF7",
        "data_edge": "#6D58A8",
        "action": "#B64234",
        "feedback": "#5E4A8A",
    }

    ax.text(
        8,
        8.55,
        "提案手法の閉ループ制御ブロック線図",
        ha="center",
        va="center",
        fontsize=22,
        fontweight="bold",
        color=colors["ink"],
    )
    ax.text(
        8,
        8.13,
        "GPをプラント，BOを制御器として，状態観測 → 制御入力 → 進化実行 → 報酬学習を繰り返す",
        ha="center",
        va="center",
        fontsize=12.5,
        color=colors["muted"],
    )

    bo = (1.05, 4.98, 3.8, 1.78)
    plant = (10.75, 4.98, 4.05, 1.78)
    state = (10.55, 2.15, 4.45, 1.58)
    reward = (5.95, 1.05, 4.3, 1.58)
    data = (1.05, 1.05, 3.9, 1.58)

    _box(
        ax,
        *bo,
        title="BO 制御器",
        body="文脈付き BO\nGP surrogate + EI",
        face=colors["bo_face"],
        edge=colors["bo_edge"],
        title_size=16.5,
        body_size=12.2,
    )
    _box(
        ax,
        *plant,
        title="多目的 GP プラント",
        body="k 世代だけ進化を実行\n交叉・突然変異・NSGA-II・archive",
        face=colors["plant_face"],
        edge=colors["plant_edge"],
        title_size=16.0,
        body_size=11.3,
    )
    _box(
        ax,
        *state,
        title="状態観測・区間統計",
        body="xℓ = [進行率, HV, ΔHV, D, 木サイズ, 停滞]\nΔHV_rate, 平均Diversity, C_k を計算",
        face=colors["state_face"],
        edge=colors["state_edge"],
        title_size=14.5,
        body_size=10.4,
    )
    _box(
        ax,
        *reward,
        title="報酬計算",
        body="rℓ = HV改善 + 多様性維持 − 制御コスト\n短い k は弱く減点",
        face=colors["reward_face"],
        edge=colors["reward_edge"],
        title_size=14.5,
        body_size=10.4,
    )
    _box(
        ax,
        *data,
        title="BO 学習データ",
        body="D_k ← (xℓ, p_c, p_m, k, rℓ)\n次の surrogate 更新に利用",
        face=colors["data_face"],
        edge=colors["data_edge"],
        title_size=14.5,
        body_size=10.5,
    )

    # Action channel.
    _arrow(
        ax,
        (bo[0] + bo[2], bo[1] + bo[3] * 0.58),
        (plant[0], plant[1] + plant[3] * 0.58),
        label="制御入力  uℓ = (p_c, p_m, k)",
        color=colors["action"],
        label_offset=(0.0, 0.34),
        lw=3.0,
    )
    ax.text(
        7.8,
        5.15,
        "操作強度と更新周期を同時に決定",
        ha="center",
        va="center",
        fontsize=10.5,
        color=colors["action"],
    )

    # Plant output to observation.
    _arrow(
        ax,
        (plant[0] + plant[2] * 0.58, plant[1]),
        (state[0] + state[2] * 0.58, state[1] + state[3]),
        label="集団 P, archive A, 世代指標",
        color="#2E7D50",
        label_offset=(1.15, -0.06),
    )

    # Observation to reward.
    _arrow(
        ax,
        (state[0], state[1] + state[3] * 0.36),
        (reward[0] + reward[2], reward[1] + reward[3] * 0.64),
        label="評価量",
        color="#6B6A16",
        rad=0.05,
        label_offset=(-0.34, -0.14),
    )

    # Reward to history.
    _arrow(
        ax,
        (reward[0], reward[1] + reward[3] * 0.50),
        (data[0] + data[2], data[1] + data[3] * 0.50),
        label="報酬 rℓ",
        color=colors["feedback"],
        label_offset=(0.0, 0.25),
    )

    # Learning data back to BO.
    _arrow(
        ax,
        (data[0] + data[2] * 0.50, data[1] + data[3]),
        (bo[0] + bo[2] * 0.50, bo[1]),
        label="モデル更新",
        color=colors["feedback"],
        label_offset=(-1.0, 0.05),
        rad=-0.10,
    )

    # State feedback to BO, drawn outside the main blocks.
    _elbow_arrow(
        ax,
        [
            (state[0], state[1] + state[3] * 0.72),
            (5.35, state[1] + state[3] * 0.72),
            (5.35, bo[1] + bo[3] * 0.04),
            (bo[0] + bo[2] * 0.77, bo[1] + bo[3] * 0.04),
        ],
        label="観測状態 xℓ を入力",
        label_xy=(5.35, 4.05),
        color="#3176A8",
        lw=2.5,
    )

    # A subtle loop guide line.
    ax.text(
        8,
        0.34,
        "閉ループの要点: BOは「今の探索状態」を見て，次の交叉率・突然変異率・更新周期を選び，得られた報酬で自分の予測モデルを更新する。",
        ha="center",
        va="center",
        fontsize=11.2,
        color=colors["ink"],
        bbox=dict(boxstyle="round,pad=0.35", fc="#FFFFFF", ec="#D8D0BD", alpha=0.96),
    )

    png_path = output_dir / "gp_bo_closed_loop_block_diagram.png"
    svg_path = output_dir / "gp_bo_closed_loop_block_diagram.svg"
    fig.savefig(png_path, dpi=240, bbox_inches="tight", facecolor=fig.get_facecolor())
    fig.savefig(svg_path, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)

    print(png_path)
    print(svg_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
