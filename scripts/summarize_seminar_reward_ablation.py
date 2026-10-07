"""Summarize one-term reward ablations and audit reward reconstruction."""
from __future__ import annotations

import argparse
import csv
from dataclasses import asdict
import json
import os
from pathlib import Path
import sys

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/bogp_mpl_cache")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import numpy as np
from scipy.stats import t, ttest_rel, wilcoxon
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from bogp.objectives import RewardConfig, compute_reward
from bogp.types import ControlInput, GPStateSnapshot

OUT = ROOT / "outputs/seminar_reward_ablation/20261001"
BASE = ROOT / "outputs/seminar_context_ablation/20261001/contextual"
ORDER = ("full", "no_hv", "no_diversity", "no_control_cost", "no_floor")
LABELS = {"full": "Full reward", "no_hv": "Without HV", "no_diversity": "Without diversity target",
          "no_control_cost": "Without update cost*", "no_floor": "Without diversity floor"}
COLORS = dict(zip(ORDER, ["#202020", "#e66101", "#5e3c99", "#0571b0", "#4d9221"]))
WEIGHTS = {"hv_term": .55, "diversity_term": .35, "control_cost": -.05,
           "floor_penalty": -.25, "stagnation_penalty": 0., "bloat_penalty": 0.}


def state_from_generation(g):
    return GPStateSnapshot(generation=g["generation"], total_generations=78,
                           hypervolume=g["archive_hypervolume"], recent_hv_delta=0.,
                           diversity=g["population_diversity"], best_fitness=0.,
                           recent_best_improvement=0., stagnation_generations=g["stagnation_generations"],
                           mean_tree_size=g["mean_tree_size"])


def audit_rewards(item):
    gs = item["generations"]
    for record in item["records"]:
        start, end = record["start_generation"], record["end_generation"]
        result = compute_reward(state_from_generation(gs[start]), state_from_generation(gs[end]),
                                RewardConfig(**item["reward_config"]),
                                ControlInput(**record["control"]),
                                [g["population_diversity"] for g in gs[start+1:end+1]])
        for key, value in asdict(result).items():
            assert abs(value-record["reward"][key]) < 1e-12, (item["method"], item["seed"], start, key)


def metrics(item):
    gs, records = item["generations"], item["records"]
    post = records[6:]
    time_diversity = np.array([g["population_diversity"] for g in gs[19:]])
    target = .6-.4*np.arange(19,79)/78
    return {
        "final_hv": gs[-1]["archive_hypervolume"],
        "gain": gs[-1]["archive_hypervolume"]-gs[18]["archive_hypervolume"],
        "auc": float(np.trapz([g["archive_hypervolume"] for g in gs[18:]],dx=1)/60),
        "final_diversity": gs[-1]["population_diversity"],
        "mean_diversity_post": float(time_diversity.mean()),
        "diversity_target_error_post": float(abs(time_diversity-target).mean()),
        "final_tree_size": gs[-1]["mean_tree_size"],
        "steps": len(records),
        "pc_time_post": sum(r["control"]["crossover_rate"]*(r["end_generation"]-r["start_generation"]) for r in post)/60,
        "pm_time_post": sum(r["control"]["mutation_rate"]*(r["end_generation"]-r["start_generation"]) for r in post)/60,
        "low_diversity_generations_post": int(sum(time_diversity<.1)),
        "stagnation_mean_post": float(np.mean([g["stagnation_generations"] for g in gs[19:]])),
        "k1_post": sum(r["control"]["update_period"]==1 for r in post),
        "k3_post": sum(r["control"]["update_period"]==3 for r in post),
        "k5_post": sum(r["control"]["update_period"]==5 for r in post),
    }


def holm(pvalues):
    order = sorted(pvalues, key=pvalues.get)
    running = 0.
    result = {}
    for i, key in enumerate(order):
        running = max(running, min(1., (len(order)-i)*pvalues[key]))
        result[key] = running
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-count", type=int, default=100)
    args = parser.parse_args()
    n = args.seed_count
    runs = {"full": [json.loads((BASE/f"seed_{s}.json").read_text()) for s in range(n)]}
    for variant in ORDER[1:]:
        runs[variant] = [json.loads((OUT/variant/f"seed_{s}.json").read_text()) for s in range(n)]
        for base, item in zip(runs["full"], runs[variant]):
            assert item["evaluations"]==1872 and len(item["generations"])==79
            assert item["generations"][:19]==base["generations"][:19]
            assert [r["control"] for r in item["records"][:6]] == [r["control"] for r in base["records"][:6]]
            assert item["controller_config"] == base["controller_config"]
    for items in runs.values():
        for item in items:
            audit_rewards(item)
    rows = [{"method": method,"seed": item["seed"], **metrics(item)} for method in ORDER for item in runs[method]]
    keys = list(metrics(runs["full"][0]))
    values = {m: {k:np.array([r[k] for r in rows if r["method"]==m]) for k in keys} for m in ORDER}
    stats = {m:{k:{"mean":float(values[m][k].mean()),"std":float(values[m][k].std()),
                  "median":float(np.median(values[m][k]))} for k in keys} for m in ORDER}
    paired = {}
    for m in ORDER[1:]:
        paired[m] = {}
        for k in keys:
            a,b = values[m][k],values["full"][k]
            d = a-b
            margin = t.ppf(.975,n-1)*d.std(ddof=1)/np.sqrt(n) if n>1 else 0.
            p = float(ttest_rel(a,b).pvalue) if np.std(d)>0 else 1.
            wp = float(wilcoxon(d).pvalue) if np.any(abs(d)>1e-12) else 1.
            paired[m][k] = {"mean":float(d.mean()),"ci95":[float(d.mean()-margin),float(d.mean()+margin)],
                            "positive":int(sum(d>1e-12)),"zero":int(sum(abs(d)<=1e-12)),"negative":int(sum(d < -1e-12)),
                            "paired_t_p":p,"wilcoxon_p":wp}
        paired[m]["identical_generation_history_seeds"] = [s for s in range(n) if runs[m][s]["generations"]==runs["full"][s]["generations"]]
    for k in keys:
        adjusted = holm({m:paired[m][k]["paired_t_p"] for m in ORDER[1:]})
        for m in ORDER[1:]:
            paired[m][k]["holm_p_across_four_ablations"] = adjusted[m]
    contribution = {}
    for phase in ("warmup", "post"):
        records = [r for item in runs["full"] for r in (item["records"][:6] if phase=="warmup" else item["records"][6:])]
        contribution[phase] = {"intervals":len(records)}
        for key,w in WEIGHTS.items():
            raw = np.array([r["reward"][key] for r in records]); v=raw*w
            contribution[phase][key] = {"signed_mean":float(v.mean()),"abs_mean":float(abs(v).mean()),
                                       "active_intervals":int(sum(abs(v)>1e-12)),
                                       "raw_positive_intervals":int(sum(raw>1e-12))}
    floor_seeds=[s for s,item in enumerate(runs["full"]) if any(r["reward"]["floor_penalty"]>0 for r in item["records"])]
    inactive=[s for s in range(n) if s not in floor_seeds]
    assert all(s in paired["no_floor"]["identical_generation_history_seeds"] for s in inactive)
    for m in ORDER:
        stats[m]["floor_active_seeds"] = [s for s,item in enumerate(runs[m]) if any(r["reward"]["floor_penalty"]>0 for r in item["records"])]
    floor_effects=[{"seed":s,"full_hv":values['full']['final_hv'][s],
                   "no_floor_hv":values['no_floor']['final_hv'][s],
                   "difference":values['no_floor']['final_hv'][s]-values['full']['final_hv'][s]}
                  for s in floor_seeds]
    payload={"n":n,"statistics":stats,"paired_ablation_minus_full":paired,
             "baseline_weighted_contributions_by_interval":contribution,"floor_active_baseline_seeds":floor_seeds,
             "floor_active_seed_effects":floor_effects,
             "audit":"All warmup controls and generation histories match through g18; all rewards independently reconstructed; 1872 evaluations/run."}
    (OUT/"analysis.json").write_text(json.dumps(payload,indent=2),encoding="utf-8")
    with (OUT/"summary_by_seed.csv").open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    plot(runs,stats,paired)
    print(json.dumps({"statistics":{m:{k:stats[m][k] for k in ('final_hv','final_diversity','steps','diversity_target_error_post')} for m in ORDER},"paired":{m:{k:paired[m][k] for k in ('final_hv','final_diversity','steps','diversity_target_error_post')} for m in ORDER[1:]},"baseline_contributions":contribution},indent=2))


def plot(runs,stats,paired):
    fig,axs=plt.subplots(1,3,figsize=(16,5.2))
    for m in ORDER:
        matrix=np.array([[g["archive_hypervolume"] for g in item["generations"]] for item in runs[m]])
        axs[0].plot(range(79),matrix.mean(0),label=LABELS[m],color=COLORS[m])
        diversity=np.array([[g["population_diversity"] for g in item["generations"]] for item in runs[m]])
        axs[1].plot(range(79),diversity.mean(0),label=LABELS[m],color=COLORS[m])
    for ax in axs[:2]:
        ax.axvline(18,color="#999999",linestyle="--");ax.set_xlabel("Generation");ax.grid(alpha=.2)
    axs[0].set_ylabel("Mean archive HV");axs[0].set_title("HV trajectory")
    axs[1].plot(range(79),.6-.4*np.arange(79)/78,color="#999999",linestyle=":",label="Diversity target")
    axs[1].axhline(.1,color="#aaaaaa",linestyle="--");axs[1].set_ylabel("Mean structural diversity");axs[1].set_title("Diversity trajectory")
    axs[0].legend(fontsize=8,loc="lower right")
    for i,m in enumerate(ORDER[1:]):
        row=paired[m]["final_hv"];lower,upper=row["ci95"]
        axs[2].errorbar(row["mean"],i,xerr=[[row["mean"]-lower],[upper-row["mean"]]],fmt="o",color=COLORS[m],capsize=4)
    axs[2].axvline(0,color="gray",linestyle="--");axs[2].set_yticks(range(4),[LABELS[m] for m in ORDER[1:]])
    axs[2].invert_yaxis();axs[2].set_xlabel("Final HV: ablation - full (95% CI)");axs[2].set_title("Paired effect of removing each term");axs[2].grid(axis="x",alpha=.2)
    fig.text(.5,.005,"* Update-cost term is a per-k constant: per-k EI cancels its level shift; see report for numerical effects.",ha="center",fontsize=8)
    fig.tight_layout(rect=[0,.035,1,1]);fig.savefig(OUT/"reward_ablation_overview.png",dpi=180);plt.close(fig)
    fig,axs=plt.subplots(1,3,figsize=(15,4.3))
    names=['hv_term','diversity_term','control_cost','floor_penalty'];short=['HV','Diversity target','Update cost','Floor penalty']
    phases=[(0,18),(18,38),(38,58),(58,78)]
    width=.19
    for j,key in enumerate(names):
        vals=[]
        for lo,hi in phases:
            rs=[r for item in runs['full'] for r in item['records'] if lo<r['end_generation']<=hi]
            vals.append(float(np.mean([r['reward'][key]*WEIGHTS[key] for r in rs])))
        axs[0].bar(np.arange(4)+(j-1.5)*width,vals,width,label=short[j])
    axs[0].axhline(0,color='gray');axs[0].set_xticks(range(4),['Warmup\n1-18','19-38','39-58','59-78']);axs[0].set_ylabel('Mean weighted contribution / interval');axs[0].set_title('Full reward: contributions');axs[0].legend(fontsize=8)
    for progress,label in [(18/78,'g18 (target 0.508)'),(.5,'g39 (target 0.400)'),(1.,'g78 (target 0.200)')]:
        d=np.linspace(0,1,201);target=.6-.4*progress
        axs[1].plot(d,.35*np.exp(-((d-target)/.15)**2),label=label)
    axs[1].set(xlabel='Interval mean diversity',ylabel='Weighted diversity reward',title='Diversity target rewards alignment');axs[1].legend(fontsize=8)
    x=np.arange(3); counts=np.array([[sum(r['control']['update_period']==k for item in runs[m] for r in item['records'][6:]) for k in (1,3,5)] for m in ORDER]); fractions=counts/counts.sum(1,keepdims=True)
    for i,m in enumerate(ORDER):axs[2].bar(x+(i-2)*.15,fractions[i],.15,label=LABELS[m],color=COLORS[m])
    axs[2].set_xticks(x,['k=1','k=3','k=5']);axs[2].set_ylabel('Share of post-warmup selections');axs[2].set_title('Update periods');axs[2].legend(fontsize=7)
    fig.tight_layout();fig.savefig(OUT/'reward_mechanisms.png',dpi=180);plt.close(fig)
    if len(runs['full']) > 75:
        fig,axs=plt.subplots(1,2,figsize=(11,4))
        for method,label,color in [('full','Full reward','#202020'),('no_floor','Without diversity floor','#4d9221')]:
            gs=runs[method][75]['generations']
            axs[0].plot(range(79),[g['archive_hypervolume'] for g in gs],label=label,color=color)
            axs[1].plot(range(79),[g['population_diversity'] for g in gs],label=label,color=color)
        for ax in axs:
            ax.axvline(18,color='gray',linestyle='--');ax.set_xlabel('Generation');ax.grid(alpha=.2);ax.legend(fontsize=9)
        axs[0].set(ylabel='Archive HV',title='Seed 75: HV recovery')
        axs[1].axhline(.1,color='gray',linestyle=':',label='Floor = 0.10')
        axs[1].set(ylabel='Structural diversity',title='Seed 75: diversity collapse and recovery')
        fig.tight_layout();fig.savefig(OUT/'floor_case_seed75.png',dpi=180);plt.close(fig)


if __name__=="__main__":
    main()
