from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import subprocess
import sys
from collections import Counter
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/bogp_mpl_cache")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import scipy
import sklearn
from bogp.benchmark_analysis import warmup_headroom

METHODS = ["plain_fixed_standard", "plain_fixed_high_mutation", "plain_fixed_high_crossover", "bogp_current"]
LABELS = {"plain_fixed_standard": "標準固定", "plain_fixed_high_mutation": "高突然変異",
          "plain_fixed_high_crossover": "高交叉", "bogp_current": "提案法"}
ENGLISH = ["Fixed standard", "Fixed high mutation", "Fixed high crossover", "BOGP"]
PROBLEMS = ["uball5d", "airfoil", "concrete"]
COLORS = ["#4477AA", "#EE7733", "#228833", "#AA3377"]


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def mean_std(values):
    array = np.asarray([item for item in values if item is not None], dtype=float)
    return (float(array.mean()), float(array.std(ddof=0))) if len(array) else (None, None)


def format_mean(values, precision=4):
    avg, std = mean_std(values)
    return "n.a." if avg is None else f"{avg:.{precision}f} ± {std:.{precision}f}"


def finite_median(values):
    finite = [value for value in values if value is not None]
    return float(np.median(finite)) if finite else None


def used_variables(expression):
    indices = set()
    if expression["op"] == "var":
        indices.add(expression["variable_index"] + 1)
    for child in expression["children"]:
        indices.update(used_variables(child))
    return indices


def main():
    parser = argparse.ArgumentParser(description="Validate and summarize completed three-problem pilots.")
    parser.add_argument("experiment_root", type=Path)
    args = parser.parse_args()
    base = args.experiment_root.resolve()
    runs, histories = [], {}
    checks = []
    for problem in PROBLEMS:
        folder = base / problem / "seminar_78_generations"
        manifest = json.loads((folder / "dataset_manifest.json").read_text())
        config = json.loads((folder / "config.json").read_text())["config"]
        expected_seeds = config["seeds"]
        assert config["total_generations"] == 78 and config["population_size"] == 24
        assert config["bo_controller_overrides"] == {} and config["reward_overrides"] == {}
        initial_hvs = {}
        for method in METHODS:
            for seed in expected_seeds:
                run_dir = folder / "runs" / method / f"seed_{seed}"
                summary = json.loads((run_dir / "summary.json").read_text())
                metrics = read_jsonl(run_dir / "generation_metrics.jsonl")
                diagnostic = read_jsonl(run_dir / "regression_diagnostics.jsonl")
                controls = read_jsonl(run_dir / "control_records.jsonl")
                assert [row["generation"] for row in metrics] == list(range(79))
                assert [row["generation"] for row in diagnostic] == list(range(79))
                assert summary["evaluations"] == 1872 and summary["final_generation"] == 78
                assert abs(summary["final_archive_hypervolume"] - metrics[-1]["archive_hypervolume"]) < 1e-12
                initial_hvs.setdefault(seed, []).append(metrics[0]["archive_hypervolume"])
                if method == "bogp_current":
                    assert [row["end_generation"] for row in controls[:6]] == [1, 2, 5, 8, 13, 18]
                    post_controls = [row for row in controls if row["start_generation"] >= 18]
                    k_counts = Counter(row["control"]["update_period"] for row in post_controls)
                    k_generations = {k: sum(row["end_generation"] - row["start_generation"]
                                          for row in post_controls if row["control"]["update_period"] == k)
                                     for k in [1, 3, 5]}
                else:
                    post_controls, k_counts, k_generations = [], {}, {}
                final = diagnostic[-1]
                warm = diagnostic[18]
                late = diagnostic[60]
                row = {"problem": problem, "method": method, "seed": seed,
                       **warmup_headroom([item["archive_hypervolume"] for item in metrics]),
                       "train_nrmse_initial": diagnostic[0]["train_nrmse_raw"],
                       "train_nrmse_warmup": warm["train_nrmse_raw"],
                       "train_nrmse_final": final["train_nrmse_raw"],
                       "post_warmup_train_nrmse_reduction": warm["train_nrmse_raw"] - final["train_nrmse_raw"],
                       "late_train_nrmse_reduction_60_to_end": late["train_nrmse_raw"] - final["train_nrmse_raw"],
                       "validation_nrmse_final": final["validation_nrmse_raw"],
                       "test_nrmse_final": final["test_nrmse_raw"], "test_r2_final": final["test_r2"],
                       "test_rmse_original_units": final["test_rmse_original_units"],
                       "train_best_tree_size": final["tree_size"],
                       "train_best_variable_count": len(used_variables(final["expression"])),
                       "mean_tree_size_final": metrics[-1]["mean_tree_size"],
                       "population_diversity_final": metrics[-1]["population_diversity"],
                       "archive_unique_objective_size": summary["archive_unique_objective_size"],
                       "training_fitness_calls_including_initial": 1896,
                       "elapsed_search_seconds": summary["wall_time_seconds"],
                       "post_warmup_bo_k_step_counts": dict(k_counts),
                       "post_warmup_bo_k_generation_counts": k_generations,
                       "expression_text": final["expression_text"], "output_dir": str(run_dir)}
                runs.append(row)
                histories[(problem, method, seed)] = (metrics, diagnostic)
        assert all(max(values) - min(values) < 1e-12 for values in initial_hvs.values())
        checks.append({"problem": problem, "run_count": len(METHODS) * len(expected_seeds),
                       "all_generations_0_through_78": True, "equal_initial_hv_per_seed": True,
                       "fitness_calls_per_run": 1896, "actual_partition_sizes": manifest["partition_sizes"],
                       "bo_warmup_boundary_verified": 18})

    aggregates = []
    numeric = [key for key, value in runs[0].items()
               if isinstance(value, (float, int)) and key != "seed"]
    for problem in PROBLEMS:
        for method in METHODS:
            group = [row for row in runs if row["problem"] == problem and row["method"] == method]
            entry = {"problem": problem, "method": method, "seed_count": len(group)}
            for metric in numeric:
                avg, std = mean_std([row[metric] for row in group])
                entry[metric + "_mean"], entry[metric + "_std_ddof0"] = avg, std
            entry["q_w_median"] = finite_median([row["warmup_improvement_fraction"] for row in group])
            entry["t90_median"] = finite_median([row["t90_finite_budget"] for row in group])
            entry["seeds_with_post_warmup_hv_gain"] = sum(row["post_warmup_hv_gain_running_max"] > 1e-9 for row in group)
            entry["seeds_with_post_warmup_train_error_reduction"] = sum(row["post_warmup_train_nrmse_reduction"] > 1e-9 for row in group)
            entry["seeds_with_late_hv_gain"] = sum(row["late_hv_gain_running_max_60_to_end"] > 1e-9 for row in group)
            aggregates.append(entry)
    paired = []
    for problem in PROBLEMS:
        proposed = {row["seed"]: row for row in runs if row["problem"] == problem and row["method"] == "bogp_current"}
        for baseline in METHODS[:-1]:
            fixed = {row["seed"]: row for row in runs if row["problem"] == problem and row["method"] == baseline}
            diffs = [proposed[seed]["hv_final"] - fixed[seed]["hv_final"] for seed in proposed]
            paired.append({"problem": problem, "baseline": baseline,
                           "paired_final_hv_difference_mean": float(np.mean(diffs)),
                           "paired_differences_by_seed": dict(zip(proposed, diffs)),
                           "wins": sum(delta > 1e-12 for delta in diffs),
                           "ties": sum(abs(delta) <= 1e-12 for delta in diffs),
                           "losses": sum(delta < -1e-12 for delta in diffs)})

    # Reproducibility evidence; no claims about isolated wall-clock benchmarks.
    source_paths = [ROOT / "src" / "bogp" / filename for filename in
                    ["symbolic_regression_benchmarks.py", "symbolic_regression_alpha.py", "formal_experiment.py",
                     "test_ver2_b_mo_engine.py", "controller.py", "objectives.py"]]
    source_paths.append(ROOT / "scripts" / "run_thesis_three_problem_pilot.py")
    environment = {"python": sys.version, "platform": platform.platform(),
                   "numpy": np.__version__, "scipy": scipy.__version__, "sklearn": sklearn.__version__,
                   "matplotlib": matplotlib.__version__,
                   "git_branch": subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip(),
                   "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                   "source_sha256": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in source_paths},
                   "execution": "3 concurrent problem processes, OMP/OPENBLAS/MKL_NUM_THREADS=1",
                   "wall_time_scope": "search only, excludes initialization, holdout diagnostics and plotting"}
    payload = {"validation_checks": checks, "runs": runs, "aggregates": aggregates,
               "paired_comparisons": paired, "environment": environment}
    (base / "analysis.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    csv_rows = [{key: value for key, value in row.items() if not isinstance(value, dict)} for row in runs]
    with (base / "pilot_metrics_by_seed.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(csv_rows[0]))
        writer.writeheader()
        writer.writerows(csv_rows)

    plt.rcParams.update({"font.size": 10})
    fig, axes = plt.subplots(3, 2, figsize=(12, 10), constrained_layout=True)
    for index, problem in enumerate(PROBLEMS):
        for method, label, color in zip(METHODS, ENGLISH, COLORS):
            group = [row for row in runs if row["problem"] == problem and row["method"] == method]
            for column, series_name in enumerate(["archive_hypervolume", "train_nrmse_raw"]):
                arrays = []
                for row in group:
                    metrics, diagnostics = histories[(problem, method, row["seed"])]
                    array = np.asarray([item[series_name] for item in (metrics if column == 0 else diagnostics)])
                    arrays.append(array)
                matrix = np.vstack(arrays)
                avg, std = matrix.mean(axis=0), matrix.std(axis=0)
                ax = axes[index, column]
                ax.plot(np.arange(79), avg, color=color, label=label, lw=1.6)
                ax.fill_between(np.arange(79), avg - std, avg + std, color=color, alpha=.10)
        for column in [0, 1]:
            ax = axes[index, column]
            ax.axvline(18, color="black", ls="--", lw=.8)
            ax.set(title=f"{problem.upper()} — {'Archive HV' if column == 0 else 'Train-best NRMSE'}",
                   xlabel="Generation (18 warm-up + 60 evaluation)", ylabel="HV" if column == 0 else "NRMSE")
            ax.grid(alpha=.2)
    axes[0, 0].legend(fontsize=9, loc="best")
    fig.savefig(base / "pilot_progress.png", dpi=180)
    plt.close(fig)

    text = ["# 3問題・各3シードの予備実験結果", "",
            "集団サイズ24、ウォームアップ18＋本評価60＝78世代。各問題4手法×3シード、計36実行。",
            "平均±標準偏差はddof=0。3回の記述的傾向であり、有意差・真の収束・本番採用を確定する結果ではない。", "",
            "q_Wは履歴最大HVの全改善のうち18世代までに得られた割合。t90は78世代までのHV改善の90%到達世代。",
            "誤差は訓練誤差最小の式（同点なら小さい木）を検索後に評価。testの値は式・制御・採否の選定に使わない。", "",
            "![世代推移](pilot_progress.png)", ""]
    for problem in PROBLEMS:
        text += [f"## {problem}", "", "| 手法 | 最終HV | 18世代後HV増加 | q_W中央値 | t90中央値 | 訓練NRMSE | 検証NRMSE | テストNRMSE |",
                 "|---|---|---|---|---|---|---|---|"]
        for method in METHODS:
            group = [row for row in runs if row["problem"] == problem and row["method"] == method]
            entry = next(row for row in aggregates if row["problem"] == problem and row["method"] == method)
            text.append(f"| {LABELS[method]} | {format_mean([r['hv_final'] for r in group])} | "
                        f"{format_mean([r['post_warmup_hv_gain_raw'] for r in group])} | {entry['q_w_median']:.1%} | "
                        f"{entry['t90_median']:.0f} | {format_mean([r['train_nrmse_final'] for r in group])} | "
                        f"{format_mean([r['validation_nrmse_final'] for r in group])} | {format_mean([r['test_nrmse_final'] for r in group])} |")
        pair = next(row for row in paired if row["problem"] == problem and row["baseline"] == "plain_fixed_high_mutation")
        text += ["", f"提案法−高突然変異の平均最終HV差: {pair['paired_final_hv_difference_mean']:+.6f}。"
                 f"勝ち/同点/負け: {pair['wins']}/{pair['ties']}/{pair['losses']}。", "",
                 "| 手法 | seed | HV(g18) | HV(g78) | ΔHV | q_W | t90 | train NRMSE(g18→g78) | 最終式サイズ |",
                 "|---|---|---|---|---|---|---|---|---|"]
        for row in [r for r in runs if r["problem"] == problem]:
            text.append(f"| {LABELS[row['method']]} | {row['seed']} | {row['hv_warmup']:.6f} | {row['hv_final']:.6f} | "
                        f"{row['post_warmup_hv_gain_raw']:.6f} | {row['warmup_improvement_fraction']:.1%} | "
                        f"{row['t90_finite_budget']} | {row['train_nrmse_warmup']:.4f} → {row['train_nrmse_final']:.4f} | {row['train_best_tree_size']} |")
        text += [""]
    text += ["## 検証と制約", "", "- 36実行すべて78世代・1872子評価（初期24を含め1896訓練fitness呼出）。",
             "- 各seedの全手法で初期HVが一致。BO初期6区間の終了世代1,2,5,8,13,18を確認。",
             "- 実データの同一入力重複は同じ分割内で保持。前処理は訓練データだけ。",
             "- 3つのGP乱数seedは同一データ分割上の反復。分割不確実性は未評価。",
             "- 実データのz-score、canonical UBall標本数、validation追加は従来Friedmanのデータ仕様とは異なる。",
             "- 元の推奨案の長期予算・関数追加・linear scalingは使わず、今回はユーザー指定のセミナー条件を優先。",
             "- HVはNRMSEを[0,5]、木サイズを[1,100]へ正規化した面積。高HVは高精度を保証しない。",
             "- q_Wやt90はこの有限予算内の相対指標。78世代で真の収束・長期改善は判定できない。",
             "- 並行実行中のwall-clockは単独実行の速度比較には使わない。", ""]
    (base / "results.md").write_text("\n".join(text), encoding="utf-8")
    print(json.dumps({"validated_run_count": len(runs),
                      "summary": [{key: row[key] for key in
                                   ["problem", "method", "hv_final_mean", "post_warmup_hv_gain_raw_mean",
                                    "q_w_median", "t90_median", "train_nrmse_final_mean",
                                    "validation_nrmse_final_mean", "test_nrmse_final_mean"]}
                                  for row in aggregates],
                      "report": str(base / "results.md")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
