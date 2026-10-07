"""Create Japanese figures/tables from saved experiments for the supervisor resume."""
from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/bogp_supervisor_mpl")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np
from scipy.stats import t, ttest_rel

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "outputs/thesis_three_problem_pilot/seminar_conditions_seed3_20261001"
ABLATION = ROOT / "outputs/seminar_context_ablation/20261001"
OUT = ROOT / "notes/figures/supervisor_comparison_20261007"
METHODS = ("plain_fixed_standard", "plain_fixed_high_mutation", "plain_fixed_high_crossover", "bogp_current")
LABELS = ("標準固定率", "高突然変異固定率", "高交叉固定率", "提案法")
COLORS = ("#4477AA", "#EE7733", "#228833", "#CC4455")
PROBLEMS = ("uball5d", "airfoil", "concrete")
PROBLEM_LABELS = ("UBall5D", "Airfoil", "Concrete")


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def mean_sd(values):
    values = np.asarray(values, dtype=float)
    return rf"\({values.mean():.4f}\pm{values.std(ddof=0):.4f}\)"


def table_tex(header, rows, columns):
    return (r"\begin{tabular}{" + columns + "}\n" + r"\toprule" + "\n" + header
            + r" \\" + "\n" + r"\midrule" + "\n" + "\n".join(rows)
            + "\n" + r"\bottomrule" + "\n" + r"\end{tabular}" + "\n")


def save_figure(fig, name):
    fig.savefig(OUT / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(OUT / f"{name}.png", bbox_inches="tight", dpi=190)
    plt.close(fig)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    font_path = ROOT / ".TinyTeX/texmf-dist/fonts/opentype/public/haranoaji/HaranoAjiGothic-Medium.otf"
    font_manager.fontManager.addfont(str(font_path))
    plt.rcParams.update({"font.family": font_manager.FontProperties(fname=str(font_path)).get_name(),
                         "font.size": 11, "axes.unicode_minus": False, "pdf.fonttype": 42})
    analysis = read_json(PILOT / "analysis.json")
    raw = analysis["runs"]
    assert len(raw) == 36
    histories = {}
    for row in raw:
        key = (row["problem"], row["method"], row["seed"])
        run_dir = PILOT / row["problem"] / "seminar_78_generations/runs" / row["method"] / f"seed_{row['seed']}"
        metrics = read_jsonl(run_dir / "generation_metrics.jsonl")
        diagnostics = read_jsonl(run_dir / "regression_diagnostics.jsonl")
        assert [g["generation"] for g in metrics] == list(range(79))
        assert np.isclose(row["hv_final"], metrics[-1]["archive_hypervolume"], rtol=0, atol=1e-12)
        assert np.isclose(row["population_diversity_final"], metrics[-1]["population_diversity"], rtol=0, atol=1e-12)
        assert np.isclose(row["train_nrmse_final"], diagnostics[-1]["train_nrmse_raw"], rtol=0, atol=1e-12)
        histories[key] = (metrics, diagnostics)

    table_rows = []
    error_rows = []
    for problem, problem_label in zip(PROBLEMS, PROBLEM_LABELS):
        for method, label in zip(METHODS, LABELS):
            rows = [r for r in raw if r["problem"] == problem and r["method"] == method]
            assert len(rows) == 3
            vals = [mean_sd([r[k] for r in rows]) for k in
                    ("hv_final", "population_diversity_final", "post_warmup_hv_gain_raw")]
            table_rows.append(" & ".join([problem_label, label] + vals) + r" \\")
            vals = [mean_sd([r[k] for r in rows]) for k in
                    ("train_nrmse_final", "validation_nrmse_final", "test_nrmse_final")]
            error_rows.append(" & ".join([problem_label, label] + vals) + r" \\")
        if problem != PROBLEMS[-1]:
            table_rows.append(r"\addlinespace[2pt]")
            error_rows.append(r"\addlinespace[2pt]")
    (OUT / "pilot_metrics_rows.tex").write_text(table_tex(
        "問題 & 手法 & 最終アーカイブHV & 最終集団多様性 & 18世代後HV増加", table_rows, "@{}llccc@{}"), encoding="utf-8")
    (OUT / "pilot_error_rows.tex").write_text(table_tex(
        "問題 & 手法 & 訓練 & 検証 & テスト", error_rows, "@{}llccc@{}"), encoding="utf-8")

    fig, axes = plt.subplots(3, 3, figsize=(11.3, 8.0), sharex=True, constrained_layout=True)
    for pi, (problem, label) in enumerate(zip(PROBLEMS, PROBLEM_LABELS)):
        for mi, method in enumerate(METHODS):
            for col, (field, is_diagnostic) in enumerate((("archive_hypervolume", False),
                                                         ("population_diversity", False),
                                                         ("train_nrmse_raw", True))):
                values = np.array([[g[field] for g in histories[(problem, method, seed)][int(is_diagnostic)]]
                                   for seed in range(3)])
                ax = axes[pi, col]
                avg, sd = values.mean(0), values.std(0)
                ax.plot(range(79), avg, color=COLORS[mi], label=LABELS[mi], linewidth=1.7)
                ax.fill_between(range(79), avg-sd, avg+sd, color=COLORS[mi], alpha=.10)
                ax.axvline(18, color="#777777", linestyle="--", linewidth=.8) if mi == 0 else None
                ax.grid(alpha=.20)
                ax.set_title(label + "：" + ("アーカイブHV", "集団多様性", "訓練誤差")[col], fontsize=12)
                ax.set_ylabel(("HV（大きいほど良い）", "多様性（0～1）", "NRMSE（小さいほど良い）")[col])
                if pi == 2:
                    ax.set_xlabel("世代")
                if col == 1:
                    ax.set_ylim(0, 1.03)
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="outside lower center", ncol=4, fontsize=11)
    save_figure(fig, "pilot_dynamics")

    paired_analysis = read_json(ABLATION / "analysis.json")
    runs = {method: [read_json(ABLATION / method / f"seed_{s}.json") for s in range(100)]
            for method in ("contextual", "noncontextual")}
    for seed, (a, b) in enumerate(zip(runs["contextual"], runs["noncontextual"])):
        assert a["records"][:6] == b["records"][:6]
        assert a["evaluations"] == b["evaluations"] == 1872
        old_dir = ROOT / "outputs/main_bo_current_friedman/sr_alpha_friedman/main_bo_current_friedman_seed100_eval60_20260603/runs/bogp_current"
        assert a["generations"] == read_jsonl(old_dir / f"seed_{seed}/generation_metrics.jsonl")
    ablation_values = {}
    for method in runs:
        ablation_values[method] = np.array([r["generations"][-1]["archive_hypervolume"] for r in runs[method]])
        stored = paired_analysis["metrics"][method]["final_hv"]
        assert np.isclose(ablation_values[method].mean(), stored["mean"], rtol=0, atol=1e-12)
        assert np.isclose(ablation_values[method].std(), stored["std"], rtol=0, atol=1e-12)
    difference = ablation_values["contextual"] - ablation_values["noncontextual"]
    assert np.isclose(ttest_rel(ablation_values["contextual"], ablation_values["noncontextual"]).pvalue,
                      paired_analysis["paired"]["final_hv"]["paired_t_p"], atol=1e-12, rtol=0)
    margin = t.ppf(.975, 99) * difference.std(ddof=1) / 10
    assert np.allclose([difference.mean()-margin, difference.mean()+margin],
                       paired_analysis["paired"]["final_hv"]["ci95"], rtol=0, atol=1e-12)
    ablation_rows = []
    for key, name in (("final_hv", "最終アーカイブHV"), ("gain", "18世代後HV増加"),
                      ("auc", "本評価中の平均HV"), ("diversity", "最終集団多様性"),
                      ("steps", "制御更新回数（全期間）")):
        cells = []
        for method in runs:
            metric = paired_analysis["metrics"][method][key]
            cells.append(rf"\({metric['mean']:.4f}\pm{metric['std']:.4f}\)")
        ablation_rows.append(" & ".join([name] + cells) + r" \\")
    (OUT / "ablation_metrics_rows.tex").write_text(table_tex(
        "指標 & 提案法（状態入力あり） & 非文脈BO（状態入力なし）", ablation_rows, "@{}lcc@{}"), encoding="utf-8")

    fig, axes = plt.subplots(1, 2, figsize=(10.2, 3.25), constrained_layout=True)
    for method, label, color in (("contextual", "提案法（状態入力あり）", COLORS[3]),
                                 ("noncontextual", "非文脈BO（状態入力なし）", COLORS[0])):
        for col, field in enumerate(("archive_hypervolume", "population_diversity")):
            values = np.array([[g[field] for g in r["generations"]] for r in runs[method]])
            axes[col].plot(range(79), values.mean(0), label=label, color=color, linewidth=2)
            axes[col].fill_between(range(79), values.mean(0)-values.std(0), values.mean(0)+values.std(0),
                                   color=color, alpha=.13)
    for col, ax in enumerate(axes):
        ax.axvline(18, color="#777777", linestyle="--", linewidth=1)
        ax.set(xlabel="世代", ylabel=("アーカイブHV", "集団多様性")[col],
               title=("アーカイブHVの推移", "集団多様性の推移")[col])
        ax.grid(alpha=.2)
        ax.legend(fontsize=9, loc="lower right")
    save_figure(fig, "ablation_dynamics")

    fig, axes = plt.subplots(1, 2, figsize=(10.2, 3.2), constrained_layout=True)
    a, b = ablation_values["contextual"], ablation_values["noncontextual"]
    boxes = axes[0].boxplot([a, b], patch_artist=True, widths=.42)
    axes[0].set_xticks([1, 2], ["提案法", "非文脈BO"])
    for box, color in zip(boxes["boxes"], (COLORS[3], COLORS[0])):
        box.set_facecolor(color)
        box.set_alpha(.25)
    offsets = np.random.default_rng(20261007).uniform(-.1, .1, 100)
    axes[0].scatter(1+offsets, a, color=COLORS[3], s=13, alpha=.6)
    axes[0].scatter(2+offsets, b, color=COLORS[0], s=13, alpha=.6)
    axes[0].set(ylabel="最終アーカイブHV", title="全100回の分布")
    axes[0].grid(axis="y", alpha=.2)
    axes[1].scatter(b, a, s=21, alpha=.65, color="#555555", edgecolors="none")
    limits = (.64, .88)
    axes[1].plot(limits, limits, linestyle="--", color="#777777")
    axes[1].set(xlim=limits, ylim=limits, xlabel="非文脈BOの最終HV", ylabel="提案法の最終HV",
                title="同じ乱数シードの対応比較")
    axes[1].grid(alpha=.2)
    save_figure(fig, "ablation_distribution")

    fig, ax = plt.subplots(figsize=(5.1, 2.8), constrained_layout=True)
    xs = np.arange(3)
    for i, (method, label, color) in enumerate((("contextual", "提案法", COLORS[3]),
                                               ("noncontextual", "非文脈BO", COLORS[0]))):
        counts = paired_analysis["metrics"][method]["k_counts_post"]
        percentages = np.array([counts[str(k)] for k in (1, 3, 5)]) / sum(counts.values()) * 100
        ax.bar(xs+(i-.5)*.34, percentages, width=.34, label=label, color=color, alpha=.85)
        for x, y in zip(xs+(i-.5)*.34, percentages):
            ax.text(x, y+1, f"{y:.1f}%", ha="center", fontsize=10)
    ax.set(xticks=xs, xticklabels=["k=1", "k=3", "k=5"], ylabel="制御区間数の割合（%）", ylim=(0, 67))
    ax.legend(fontsize=10)
    ax.grid(axis="y", alpha=.2)
    save_figure(fig, "ablation_k_selection")
    report = {"pilot_runs_checked": 36, "paired_seeds_checked": 100,
              "original_contextual_histories_equal": True, "warmup_histories_equal": True,
              "sd_convention": "ddof=0", "training_calls_per_run_including_initial": 1896,
              "paired_mean_hv_difference": float(difference.mean()),
              "paired_hv_ci95": [float(difference.mean()-margin), float(difference.mean()+margin)],
              "artifact_date": "2026-10-07", "experiment_date": "2026-10-01"}
    (OUT / "source_validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
